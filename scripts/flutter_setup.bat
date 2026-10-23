@echo off
cd /d "%~dp0..\apps\mobile"
flutter create --project-name personal_swing_intelligence --platforms=android,ios .
if errorlevel 1 exit /b 1
python ..\..\scripts\finalize_flutter.py
flutter pub get
flutter analyze
echo.
echo Open Android emulator, then run flutter run
pause
