#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../apps/mobile"
if ! command -v flutter >/dev/null 2>&1; then echo 'Flutter stable SDK is required: https://docs.flutter.dev/get-started/install'; exit 1; fi
# Flutter create populates platform files, preserving existing lib/ and pubspec.yaml.
flutter create --project-name personal_swing_intelligence --platforms=android,ios .
python3 ../../scripts/finalize_flutter.py
flutter pub get
flutter analyze
printf '\nOpen Android emulator, then run: cd apps/mobile && flutter run\n'
