"""Optional Chromium UI smoke with stubbed API data; run with Playwright + chromium.

This checks rendering and JS events, NOT real browser-to-server networking or Android.
"""
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
os.environ.setdefault('SWING_DATA_MODE','demo')
os.environ.setdefault('SWING_DB_PATH','/tmp/swing_ui_smoke.db')
from fastapi.testclient import TestClient
from app import main
from app.storage import Store
# Ensure fixture uses new run schema, never cached legacy SQLite snapshots.
fixture_dir = TemporaryDirectory(prefix="swing-ui-smoke-")
main.store = Store(Path(fixture_dir.name) / "smoke.db")
app = main.app
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'web'
api=TestClient(app)
mock={endpoint:api.get('/v1/'+endpoint).json() for endpoint in ('meta','opportunities','watchlist','journal/trades','screeners')}
html=(WEB/'index.html').read_text()
css='\n'.join(x for x in (WEB/'styles.css').read_text().splitlines() if not x.startswith('@import'))
html=html.replace('<link rel="stylesheet" href="/static/styles.css" />',f'<style>{css}</style>')
script=(WEB/'app.js').read_text()
values=json.dumps(mock,ensure_ascii=False).replace('</','<\\/')
head=(f'<script>const MOCK={values}; window.fetch=async function(url){{let k=String(url).replace(/^\\/v1\\//,"");'
      'return new Response(JSON.stringify(MOCK[k]||{detail:"Not mocked"}),'
      '{status:MOCK[k]?200:404,headers:{"Content-Type":"application/json"}});};</script>')
html=html.replace('<script src="/static/app.js"></script>',head+'<script>'+script+'</script>')
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.getenv('CHROME_PATH','/usr/bin/chromium'),headless=True,
                              args=['--no-sandbox','--disable-dev-shm-usage'])
    for width,height in ((1440,900),(390,844)):
        page=browser.new_page(viewport={'width':width,'height':height})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content(html,wait_until='load')
        page.locator('[data-asset]').first.wait_for()
        assert page.locator('[data-asset]').count()>0
        page.locator('[data-asset]').first.click()
        assert page.locator('.modal').count()==1
        assert page.get_by_text('Swing Research Gate V2').count()==1
        assert page.get_by_text('Execution: NOT VERIFIED.').count()==1
        assert not errors,errors
        page.locator('#close-modal').click()
        explore_nav = '.sidebar [data-page="explore"]' if width>700 else '.mobile-tabs [data-page="explore"]'
        page.locator(explore_nav).click()
        initial=page.locator('[data-asset]').count()
        page.locator('#filter-excluded').check()
        assert page.locator('[data-asset]').count()>=initial
        page.locator('#filter-excluded').uncheck()
        assert page.locator('[data-asset]').count()==initial
        nav = '.sidebar [data-page="builder"]' if width>700 else '.mobile-tabs [data-page="builder"]'
        page.locator(nav).click()
        assert page.locator('#rule-list .rule').count()==1
        assert not errors,errors
        print(f'PASS browser mocked API rendering {width}x{height} · asset modal · rule builder · 0 pageerrors')
        page.close()
    browser.close()
