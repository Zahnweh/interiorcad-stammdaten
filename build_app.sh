#!/bin/bash
# ── interiorcad Stammdaten Tool – App Builder ─────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/interiorcad_stammdaten.py"
ICON="$SCRIPT_DIR/AppIcon.icns"
APP_NAME="interiorcad Stammdaten"

echo "🔧 Prüfe Python..."
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 nicht gefunden."
    exit 1
fi
echo "✅ Python: $(python3 --version)"

echo ""
echo "🔧 Installiere pyinstaller..."
pip3 install pyinstaller --quiet --break-system-packages 2>/dev/null || \
pip3 install pyinstaller --quiet
echo "✅ pyinstaller: $(pyinstaller --version)"

echo ""
echo "🏗  Baue App..."
cd "$SCRIPT_DIR"

# Alte Build-Artefakte entfernen
rm -rf build dist "$APP_NAME.spec"

pyinstaller \
    --windowed \
    --onefile \
    --name "$APP_NAME" \
    --icon "$ICON" \
    --osx-bundle-identifier "com.interiorcad.stammdaten" \
    --hidden-import tkinter \
    --hidden-import tkinter.ttk \
    --hidden-import tkinter.filedialog \
    --hidden-import tkinter.messagebox \
    "$PY_SCRIPT"

echo ""
if [ -d "dist/$APP_NAME.app" ]; then
    echo "✅ App erfolgreich gebaut!"
    echo "📦 Speicherort: $SCRIPT_DIR/dist/$APP_NAME.app"
    open "dist/"
else
    echo "❌ Build fehlgeschlagen."
    exit 1
fi
