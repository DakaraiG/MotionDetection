#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install opencv-python pillow numpy pyinstaller

pyinstaller --noconfirm --clean MotionDetection.spec

INFO_PLIST="dist/MotionDetection.app/Contents/Info.plist"
if [[ -f "$INFO_PLIST" ]]; then
  /usr/libexec/PlistBuddy -c "Set :NSCameraUsageDescription MotionDetection needs camera access to show the live feed." "$INFO_PLIST" \
    || /usr/libexec/PlistBuddy -c "Add :NSCameraUsageDescription string MotionDetection needs camera access to show the live feed." "$INFO_PLIST"
  /usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier com.dakaraig.motiondetection" "$INFO_PLIST" \
    || /usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string com.dakaraig.motiondetection" "$INFO_PLIST"
fi

codesign --deep --force --sign - "dist/MotionDetection.app"

echo "Built + signed: dist/MotionDetection.app"
