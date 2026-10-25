# Linux GUI launcher

The Debian packages install a `Sreon` desktop entry and the `sreon-gui` launcher. It starts the SPRFST engine, serves Sreon's internal pages locally, then opens them in Chromium app-window mode when available (or the system default browser otherwise). External web sites are handed off to the system browser; this is not yet a complete standalone browser shell.

`tools/package_linux.sh <sprfst-binary> <amd64|arm64> [output.deb]` builds the Debian package. `artifacts/linuxins` is the self-contained amd64/arm64 installer and starts `sreon-gui` after installation.
