"""Post flutter-create platform configuration. Debug emulator HTTP only; release uses HTTPS."""
from pathlib import Path
import xml.etree.ElementTree as ET

mobile=Path(__file__).resolve().parents[1]/'apps'/'mobile'
manifest=mobile/'android'/'app'/'src'/'main'/'AndroidManifest.xml'
if manifest.is_file():
    text=manifest.read_text()
    permission='<uses-permission android:name="android.permission.INTERNET" />'
    text=text.replace('android:label="personal_swing_intelligence"', 'android:label="Swing Intelligence"')
    if permission not in text:
        text=text.replace('<application',permission+'\n    <application',1)
    manifest.write_text(text)
    debug=mobile/'android'/'app'/'src'/'debug'/'AndroidManifest.xml'
    debug.parent.mkdir(parents=True,exist_ok=True)
    # Flutter debug-only cleartext access for local emulator; not release builds.
    debug.write_text('<?xml version="1.0" encoding="utf-8"?>\n<manifest xmlns:android="http://schemas.android.com/apk/res/android"><application android:usesCleartextTraffic="true" /></manifest>\n')
    print('Configured Android INTERNET permission and DEBUG-ONLY localhost HTTP access.')
else:
    raise SystemExit('Missing AndroidManifest.xml; run flutter create first.')
