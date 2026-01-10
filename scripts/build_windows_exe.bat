@echo off
setlocal

cd /d "%~dp0\\.."

python -m venv .venv
call .venv\\Scripts\\activate.bat
python -m pip install --upgrade pip
python -m pip install opencv-python pillow numpy pyinstaller

pyinstaller ^
  --windowed ^
  --name MotionDetection ^
  --noconfirm ^
  --clean ^
  --collect-all cv2 ^
  --collect-all PIL ^
  src\\main.py

endlocal
