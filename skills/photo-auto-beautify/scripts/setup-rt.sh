#!/usr/bin/env bash
# Install the RawTherapee Linux AppImage next to the skill and extract it.
# No root, no FUSE: AppImage self-extraction is used, so this also works in WSL.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${RT_INSTALL_DIR:-$HERE/../../rt-5.13}"
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    --install-dir=*) INSTALL_DIR="${arg#*=}" ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

case "$(uname -m)" in
  x86_64|amd64) ASSET="RawTherapee_5.13_x86_64_release.AppImage" ;;
  arm64|aarch64) ASSET="RawTherapee_5.13_arm64_release.AppImage" ;;
  *) echo "unsupported architecture: $(uname -m)" >&2; exit 2 ;;
esac

URL="https://github.com/RawTherapee/RawTherapee/releases/download/5.13/$ASSET"
BIN="$INSTALL_DIR/squashfs-root/usr/bin/rawtherapee-cli"
if [ -x "$BIN" ] && [ "$FORCE" -ne 1 ]; then
  echo "RawTherapee already installed: $BIN"
  exit 0
fi

mkdir -p "$INSTALL_DIR"
APPIMAGE="${RT_APPIMAGE:-$INSTALL_DIR/RawTherapee.AppImage}"
if [ ! -f "$APPIMAGE" ]; then
  echo "Downloading RawTherapee 5.13 for Linux ($(uname -m))..."
  if command -v curl >/dev/null 2>&1; then
    curl -L --fail --retry 3 -o "$APPIMAGE" "$URL"
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$APPIMAGE" "$URL"
  else
    echo "curl or wget is required" >&2
    exit 1
  fi
fi

if [ -n "${RT_SHA256:-}" ]; then
  echo "$RT_SHA256  $APPIMAGE" | sha256sum -c -
fi

chmod +x "$APPIMAGE"
TMP="$(mktemp -d "$INSTALL_DIR/.extract-XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
(
  cd "$TMP"
  "$APPIMAGE" --appimage-extract >/dev/null
)
rm -rf "$INSTALL_DIR/squashfs-root"
mv "$TMP/squashfs-root" "$INSTALL_DIR/squashfs-root"
"$BIN" -v | head -n 1
echo "Installed: $INSTALL_DIR/squashfs-root"
echo "Pipeline default RT root: $INSTALL_DIR/squashfs-root/usr/bin"
