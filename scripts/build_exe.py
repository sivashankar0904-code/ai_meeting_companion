"""Build the Windows .exe with PyInstaller.

    python scripts/build_exe.py                      # GPU libraries + Tesseract bundled if found
    python scripts/build_exe.py --no-gpu             # much smaller; speech recognition runs on the CPU
    python scripts/build_exe.py --tesseract-dir none # do not bundle Tesseract (it must be installed / TESSERACT_CMD)
    python scripts/build_exe.py --include-env        # also copy your .env (contains your API key!)

Result: dist/<name>/<name>.exe, a windowed app (no console, no taskbar button, no tray icon), with
your ``context/`` folder, ``.env.example`` and (optionally) Tesseract next to it. Everything the user
edits lives beside the exe, never inside it: .env, context/, tesseract/.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ENTRY = ROOT / "scripts" / "exe_entry.py"
DEFAULT_TESSERACT = Path(r"C:\Program Files\Tesseract-OCR")

# Packages that load files or DLLs dynamically, which PyInstaller's import analysis cannot see.
COLLECT_ALL = [
    "faster_whisper", "ctranslate2", "av", "onnxruntime", "tokenizers", "huggingface_hub",
    "sounddevice", "pyaudiowpatch", "pytesseract", "mss",
    "psycopg", "psycopg_binary", "anthropic", "langchain_anthropic", "langchain_core",
]
COLLECT_SUBMODULES = ["sqlalchemy.dialects", "pynput", "langchain_core"]
HIDDEN_IMPORTS = ["pynput.keyboard._win32", "pynput.mouse._win32", "pynput._util.win32"]
EXCLUDES = ["tkinter", "matplotlib", "pytest", "IPython", "notebook"]

HOW_TO = """AI Meeting Companion

1. Copy .env.example to .env (in this folder) and fill in ANTHROPIC_API_KEY and the DB_* settings.
2. Put your resume / job description / notes (.md or .txt) in the context\\ folder.
3. Double-click {exe}. There is no window in the taskbar and no tray icon: the overlay appears
   top-right. Hotkeys (change them in .env):
     Ctrl+Shift+H  show / hide         Ctrl+Shift+A  suggest an answer   Ctrl+Shift+S  screenshot
     Ctrl+Shift+I  focus the input     Ctrl+Shift+T  click-through       Ctrl+Shift+Q  QUIT
4. To change what the assistants say without rebuilding, put an edited copy of a prompt in a prompts\\ folder here
   (e.g. prompts\\screen_analyzer.md, conversor.md, chat.md, shared_memory.md); it overrides the built-in one.
5. Problems? See ai-meeting-companion.log here, or run {exe} --selftest for a health report (selftest.txt).

The first start downloads the speech model (about 460 MB) and needs internet.
"""


def run(cmd: list[str]) -> None:
    print("\n>", " ".join(cmd[:6]), "...\n", flush=True)
    subprocess.run(cmd, check=True)


def ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
        return
    except ImportError:
        pass
    print("PyInstaller is not installed; installing it into this environment...", flush=True)
    if shutil.which("uv"):
        run(["uv", "pip", "install", "--python", sys.executable, "pyinstaller>=6"])
    else:
        run([sys.executable, "-m", "pip", "install", "pyinstaller>=6"])


def nvidia_bin_dirs() -> list[tuple[str, Path]]:
    """(package name, its bin folder) for the pip-installed cuBLAS / cuDNN libraries."""
    try:
        import nvidia
    except ImportError:
        return []
    found = []
    for root in nvidia.__path__:
        for bin_dir in sorted(Path(root).glob("*/bin")):
            if bin_dir.parent.name != "cuda_nvrtc":  # not needed for speech recognition, saves space
                found.append((bin_dir.parent.name, bin_dir))
    return found


def folder_size_mb(path: Path) -> float:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1e6


def build(args: argparse.Namespace) -> Path:
    dist, work = ROOT / "dist", ROOT / "build"
    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--windowed",  # no console window, and no console icon on the taskbar
        "--name", args.name, "--distpath", str(dist), "--workpath", str(work), "--specpath", str(work),
        "--paths", str(SRC), "--collect-data", "ai_meeting_companion",
    ]
    for pkg in COLLECT_ALL:
        cmd += ["--collect-all", pkg]
    for pkg in COLLECT_SUBMODULES:
        cmd += ["--collect-submodules", pkg]
    for name in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", name]
    for name in EXCLUDES:
        cmd += ["--exclude-module", name]
    if args.icon:
        cmd += ["--icon", str(Path(args.icon).resolve())]
    if not args.no_gpu:
        libs = nvidia_bin_dirs()
        if not libs:
            print("GPU libraries not installed (uv pip install -e \".[gpu]\"); building CPU-only.", flush=True)
        for package, bin_dir in libs:
            cmd += ["--add-binary", f"{bin_dir / '*.dll'};nvidia/{package}/bin"]
    cmd.append(str(ENTRY))
    run(cmd)
    return dist / args.name


def add_user_files(app: Path, args: argparse.Namespace) -> None:
    exe = f"{args.name}.exe"

    context_src = ROOT / "context"
    if context_src.is_dir():
        shutil.copytree(context_src, app / "context", dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__"))
    else:
        (app / "context").mkdir(exist_ok=True)

    shutil.copy2(ROOT / ".env.example", app / ".env.example")
    if args.include_env:
        if (ROOT / ".env").is_file():
            shutil.copy2(ROOT / ".env", app / ".env")
            print("Copied .env into the build (it contains your API key: do not share this folder).")
        else:
            print("--include-env given but there is no .env to copy.")

    if args.tesseract_dir.lower() != "none":
        source = DEFAULT_TESSERACT if args.tesseract_dir == "auto" else Path(args.tesseract_dir)
        if (source / "tesseract.exe").is_file():
            shutil.copytree(source, app / "tesseract", dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("*.html", "unins*"))
            print(f"Bundled Tesseract from {source}")
        else:
            print(f"Tesseract not found at {source}; not bundled (install it or set TESSERACT_CMD).")

    (app / "HOW_TO_RUN.txt").write_text(HOW_TO.format(exe=exe), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", default="AIMeetingCompanion")
    parser.add_argument("--no-gpu", action="store_true", help="do not bundle the ~1.5 GB NVIDIA libraries")
    parser.add_argument("--tesseract-dir", default="auto", help="'auto' (default), a folder, or 'none'")
    parser.add_argument("--include-env", action="store_true", help="copy your .env next to the exe")
    parser.add_argument("--icon", help="optional .ico for the exe file")
    args = parser.parse_args()

    ensure_pyinstaller()
    app = build(args)
    add_user_files(app, args)

    exe = app / f"{args.name}.exe"
    print(f"\nBuilt {exe}  ({folder_size_mb(app) / 1000:.2f} GB folder)")
    print("Next: copy .env.example to .env in that folder, then run the exe (or run it with --selftest).")
    return 0 if exe.is_file() else 1


if __name__ == "__main__":
    raise SystemExit(main())
