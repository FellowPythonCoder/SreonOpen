#!/bin/sh
# Build a Sreon Debian package from a Linux SPRFST executable.
set -eu
if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  echo "Usage: $0 <sprfst-binary> <amd64|arm64> [output.deb]" >&2
  exit 2
fi
BIN=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
ARCH=$2
case "$ARCH" in amd64|arm64) ;; *) echo "Unsupported Debian architecture: $ARCH" >&2; exit 2;; esac
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
OUT=${3:-"$ROOT/artifacts/sreon-${ARCH}.deb"}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
PKG="$TMP/pkg"
mkdir -p "$PKG/DEBIAN" "$PKG/usr/lib/sreon/bin" "$PKG/usr/share/sreon" \
  "$PKG/usr/bin" "$PKG/usr/share/applications" "$PKG/usr/share/icons/hicolor/512x512/apps"
cp "$BIN" "$PKG/usr/lib/sreon/bin/sprfst"
cp -R "$ROOT/engine" "$ROOT/std" "$ROOT/rules" "$ROOT/guidebook" "$ROOT/examples" "$PKG/usr/share/sreon/"
install -m 644 "$ROOT/packaging/linux/sreon_gui.py" "$PKG/usr/share/sreon/sreon_gui.py"
install -m 755 "$ROOT/packaging/linux/sreon-gui" "$PKG/usr/bin/sreon-gui"
install -m 644 "$ROOT/packaging/linux/sreon.desktop" "$PKG/usr/share/applications/sreon.desktop"
install -m 644 "$ROOT/assets/logo/Sreon-1024.png" "$PKG/usr/share/icons/hicolor/512x512/apps/sreon.png"
cat > "$PKG/DEBIAN/control" <<EOF
Package: sreon-browser
Version: 1.1.0
Section: web
Priority: optional
Architecture: $ARCH
Depends: python3, xdg-utils
Maintainer: Sreon <maintainers@sreon.example>
Description: Sreon graphical interface and SPRFST engine
 A lightweight GUI host for Sreon's internal browser pages using the
 system web browser, together with the SPRFST runtime and engine resources.
 External websites are handed off to the system browser.
EOF
mkdir -p "$(dirname "$OUT")"
dpkg-deb --root-owner-group --build "$PKG" "$OUT"
echo "Built $OUT"
