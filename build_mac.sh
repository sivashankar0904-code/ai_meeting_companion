#!/usr/bin/env bash
# Builds the macOS app into one folder (like build_exe.ps1 does on Windows) and runs the self-test.
#
#   ./build_mac.sh                  dist/AIMeetingCompanion/ = the .app + .env + context/ + HOW_TO_RUN.txt
#   ./build_mac.sh --dest ~/Meeting put the folder there instead (a rebuild replaces only the .app)
#   ./build_mac.sh --open           open the app when done (starts a real session)
#   ./build_mac.sh --dock           keep a Dock icon (default: none)
#   ./build_mac.sh --no-env         do not copy .env into the folder
#   ./build_mac.sh --skip-build     do not rebuild; only refresh the folder and re-run the self-test
#   ./build_mac.sh --sign-identity "Apple Development: you@example.com (TEAMID)"
#                                   sign with a keychain certificate (or set CODESIGN_IDENTITY) so macOS keeps
#                                   the Accessibility / Input Monitoring grants across rebuilds; default is ad hoc
#
# The app reads .env, context/ and prompts/ from the folder that holds the .app, so move the folder as a whole.
# Files already in the folder (an edited .env or context/) are never overwritten. Nothing here reads .env.
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="AIMeetingCompanion"
DEST="" OPEN=0 SKIP_BUILD=0 PY_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dest) DEST="${2:?--dest needs a folder}"; PY_ARGS+=(--dest "$DEST"); shift ;;
    --open) OPEN=1 ;;
    --dock) PY_ARGS+=(--dock) ;;
    --no-env) PY_ARGS+=(--no-env) ;;
    --skip-build) SKIP_BUILD=1 ;;
    --sign-identity) PY_ARGS+=(--sign-identity "${2:?--sign-identity needs a certificate name}"); shift ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1 (try --help)"; exit 2 ;;
  esac
  shift
done

step() { printf '\n==> %s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*"; }

[[ "$(uname)" == "Darwin" ]] || { echo "This script is for macOS; use build_exe.ps1 on Windows."; exit 1; }

step "Checking prerequisites"
command -v uv >/dev/null || { echo "uv is required (brew install uv)."; exit 1; }
[[ -x .venv/bin/python ]] || { echo "Creating the virtual environment"; uv venv .venv; }
command -v tesseract >/dev/null || warn "Tesseract not found: screenshots will not work (brew install tesseract)."
system_profiler SPAudioDataType 2>/dev/null | grep -qi blackhole \
  || warn "BlackHole not found: meeting audio cannot be captured (brew install blackhole-2ch, then reboot)."
if pgrep -f "$APP_NAME.app/Contents/MacOS" >/dev/null; then
  echo "$APP_NAME is running. Quit it first (Ctrl+Shift+Q), then run this script again."
  exit 1
fi

FOLDER="${DEST:-dist/$APP_NAME}"
FOLDER="$(mkdir -p "$FOLDER" && cd "$FOLDER" && pwd)"

if [[ $SKIP_BUILD -eq 0 ]]; then
  step "Installing Python dependencies"
  uv pip install --python .venv/bin/python -e ".[build]"
  step "Building (a few minutes)"
  .venv/bin/python scripts/build_app_macos.py ${PY_ARGS[@]+"${PY_ARGS[@]}"}
else
  [[ -d "$FOLDER/$APP_NAME.app" ]] || { echo "--skip-build given but $FOLDER/$APP_NAME.app does not exist."; exit 1; }
fi

step "Self-test (run from / so it uses only the folder's own .env)"
(cd / && "$FOLDER/$APP_NAME.app/Contents/MacOS/$APP_NAME" --selftest --quiet) \
  || warn "Self-test reported problems: see $FOLDER/selftest.txt"

cat <<MSG

Done: $FOLDER
  $APP_NAME.app   .env   context/   HOW_TO_RUN.txt
First launch: allow Microphone, and add the app under System Settings > Privacy & Security >
Screen Recording, Accessibility ("Device Control and Data Access") and Input Monitoring. Ad-hoc builds lose
these after every rebuild (run tccutil reset ... com.local.aimeetingcompanion, then add them again); a build
signed with --sign-identity keeps them.
Meeting audio: set the Multi-Output Device (headset + BlackHole 2ch) as the sound output.
Quit the app with Ctrl+Shift+Q. Log: $FOLDER/ai-meeting-companion.log
MSG

if [[ $OPEN -eq 1 ]]; then open "$FOLDER/$APP_NAME.app"; fi
