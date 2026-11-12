"""Build the macOS app folder with PyInstaller (the Mac counterpart of build_exe.py).

    uv run python scripts/build_app_macos.py                    # dist/AIMeetingCompanion/
    uv run python scripts/build_app_macos.py --dest ~/Meeting   # assemble the folder there instead
    uv run python scripts/build_app_macos.py --dock             # keep a Dock icon (default: none)
    uv run python scripts/build_app_macos.py --no-env           # do not copy your .env (it holds your API key)
    uv run python scripts/build_app_macos.py --sign-identity "Apple Development: you@example.com (TEAMID)"

Result: a folder with ``AIMeetingCompanion.app`` and, beside it, everything you edit: ``.env``, ``context/``,
``.env.example``, ``HOW_TO_RUN.txt`` (and later ``prompts/``, the log). The app reads those files from its own
folder, so move the whole folder together. Re-running replaces only the .app; files already in the folder
(an edited .env or context/) are kept. Tesseract is not bundled: ``brew install tesseract``. By default the
app is signed ad hoc, so macOS forgets Accessibility / Input Monitoring after every rebuild; sign with a keychain
certificate (--sign-identity or $CODESIGN_IDENTITY) and the grants survive rebuilds.
"""

from __future__ import annotations

import argparse
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_exe import EXCLUDES, SRC, ENTRY, ROOT, ensure_pyinstaller, folder_size_mb, run  # noqa: E402

sys.path.insert(0, str(SRC))
from ai_meeting_companion.launcher import HOW_TO_MAC  # noqa: E402

BUNDLE_ID = "com.local.aimeetingcompanion"
COLLECT_ALL = [
    "faster_whisper", "ctranslate2", "av", "onnxruntime", "tokenizers", "huggingface_hub",
    "sounddevice", "_sounddevice_data", "pytesseract", "mss",
    "psycopg", "psycopg_binary", "anthropic", "langchain_anthropic", "langchain_core",
]
COLLECT_SUBMODULES = ["sqlalchemy.dialects", "pynput", "langchain_core"]
HIDDEN_IMPORTS = [
    "pynput.keyboard._darwin", "pynput.mouse._darwin", "pynput._util.darwin",
    "Quartz", "objc", "AppKit", "Foundation", "CoreFoundation", "ApplicationServices",
]
MIC_REASON = "AI Meeting Companion transcribes your voice during meetings."
STAGING = ROOT / "build" / "pyinstaller_dist"  # dist/<name>/ is PyInstaller's own raw folder, so stage elsewhere


def build(args: argparse.Namespace) -> Path:
    work = ROOT / "build"
    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
        "--name", args.name, "--distpath", str(STAGING), "--workpath", str(work / "work"), "--specpath", str(work),
        "--osx-bundle-identifier", BUNDLE_ID, "--paths", str(SRC), "--collect-data", "ai_meeting_companion",
        "--add-data", f"{ROOT / '.env.example'}:.",
    ]
    for pkg in COLLECT_ALL:
        cmd += ["--collect-all", pkg]
    for pkg in COLLECT_SUBMODULES:
        cmd += ["--collect-submodules", pkg]
    for name in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", name]
    for name in EXCLUDES:
        cmd += ["--exclude-module", name]
    cmd.append(str(ENTRY))
    run(cmd)
    return STAGING / f"{args.name}.app"


def patch_and_sign(app: Path, dock: bool, identity: str) -> None:
    """Add the permission text macOS requires, hide the Dock icon, then sign again (editing breaks the signature).

    ``identity`` "-" is an ad-hoc signature (new hash every build, so macOS forgets the privacy grants). A named
    certificate from the keychain keeps the same designated requirement across builds, so grants survive."""
    plist_path = app / "Contents" / "Info.plist"
    info = plistlib.loads(plist_path.read_bytes())
    info["NSMicrophoneUsageDescription"] = MIC_REASON
    info["LSUIElement"] = not dock
    plist_path.write_bytes(plistlib.dumps(info))
    run(["codesign", "--force", "--deep", "--sign", identity, str(app)])
    print("Signed ad hoc (privacy grants are lost on every rebuild)." if identity == "-" else f"Signed with {identity!r}.")


def assemble(app: Path, args: argparse.Namespace) -> Path:
    """Put the .app and the files you edit into one folder. Existing files there are never overwritten."""
    folder = Path(args.dest).expanduser().resolve() if args.dest else ROOT / "dist" / args.name
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / app.name
    if target.exists():
        shutil.rmtree(target)
    subprocess.run(["ditto", str(app), str(target)], check=True)  # keeps the signature and symlinks intact
    shutil.rmtree(app)

    context = folder / "context"
    context.mkdir(exist_ok=True)
    for f in sorted((ROOT / "context").glob("*.md")) if (ROOT / "context").is_dir() else []:
        if f.name != "README.md" and not (context / f.name).exists():
            shutil.copy2(f, context / f.name)
            print(f"Copied context/{f.name}")
    shutil.copy2(ROOT / ".env.example", folder / ".env.example")
    env_src, env_dst = ROOT / ".env", folder / ".env"
    if args.no_env:
        print("Not copying .env (--no-env).")
    elif not env_src.is_file():
        print("No .env in the project: create one in the folder from .env.example.")
    elif env_dst.exists():
        print(".env already in the folder; left unchanged.")
    else:
        shutil.copy2(env_src, env_dst)
        env_dst.chmod(0o600)
        print("Copied .env into the folder (it contains your API key: do not share this folder).")
    (folder / "HOW_TO_RUN.txt").write_text(HOW_TO_MAC, encoding="utf-8")
    return folder


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", default="AIMeetingCompanion")
    parser.add_argument("--dest", help="assemble the folder here instead of dist/<name>")
    parser.add_argument("--dock", action="store_true", help="show a Dock icon")
    parser.add_argument("--no-env", action="store_true", help="do not copy .env into the folder")
    parser.add_argument(
        "--sign-identity", default=os.environ.get("CODESIGN_IDENTITY", "-"),
        help="keychain certificate to sign with (see `security find-identity -p codesigning`); default: $CODESIGN_IDENTITY or ad hoc",
    )
    args = parser.parse_args()
    if sys.platform != "darwin":
        print("This script builds the macOS app; use build_exe.ps1 on Windows.")
        return 1
    ensure_pyinstaller()
    app = build(args)
    patch_and_sign(app, args.dock, args.sign_identity)
    folder = assemble(app, args)
    print(f"\nBuilt {folder}  ({folder_size_mb(folder) / 1000:.2f} GB)")
    print(f"Next: open {folder / (args.name + '.app')} (the folder's .env and context/ are used).")
    return 0 if (folder / f"{args.name}.app").is_dir() else 1


if __name__ == "__main__":
    raise SystemExit(main())
