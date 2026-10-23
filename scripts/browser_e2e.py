"""Optional actual loopback browser test. Requires playwright + Chromium.

python scripts/browser_e2e.py
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='psi-browser-') as temp:
    env = {**os.environ, 'SWING_DB_PATH': str(Path(temp)/'testing.db'),
           'SWING_DATA_MODE': 'demo', 'SWING_API_TOKEN': '', 'SWING_HOST': '127.0.0.1'}
    process = subprocess.Popen([sys.executable, 'scripts/launch.py', '--port', '8149'],
                               cwd=ROOT, env=env, stdout=subprocess.DEVNULL,
                               stderr=subprocess.STDOUT)
    try:
        base = 'http://127.0.0.1:8149/'
        for _ in range(90):
            try:
                if httpx.get(base + 'health/live', timeout=1).status_code == 200:
                    break
            except httpx.RequestError:
                pass
            time.sleep(.1)
        else:
            raise RuntimeError('Local server did not respond')
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=os.getenv('CHROME_PATH', '/usr/bin/chromium'),
                                        args=['--no-sandbox', '--disable-dev-shm-usage'])
            for width, height in ((1440, 900), (390, 844)):
                page = browser.new_page(viewport={'width': width, 'height': height})
                errors = []
                page.on('pageerror', lambda err: errors.append(str(err)))
                page.goto(base, wait_until='domcontentloaded')
                page.locator('[data-asset]').first.wait_for(timeout=15000)
                page.locator('[data-asset]').first.click()
                page.locator('#close-modal').click()
                nav = '.sidebar [data-page="explore"]' if width > 700 else '.mobile-tabs [data-page="explore"]'
                page.locator(nav).click()
                page.locator('#filter-excluded').wait_for()
                start = len(page.locator('[data-asset]').all())
                page.locator('#filter-excluded').check()
                extended = len(page.locator('[data-asset]').all())
                assert extended >= start, f'Excluded toggle shrank list: {start} -> {extended}'
                page.locator('#filter-excluded').uncheck()
                assert len(page.locator('[data-asset]').all()) == start
                nav = '.sidebar [data-page="builder"]' if width > 700 else '.mobile-tabs [data-page="builder"]'
                page.locator(nav).click()
                assert page.locator('#rule-list .rule').count() >= 1
                assert not errors, errors
                print(f'PASS actual browser {width}x{height}, API, assets, filters and rule builder')
                page.close()
            browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
