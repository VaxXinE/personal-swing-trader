"""Launch real loopback HTTP and verify root + API, no internet provider calls."""
import os,subprocess,sys,time
from pathlib import Path
import httpx
root=Path(__file__).resolve().parents[1]
port='8139'
env={**os.environ,'SWING_DATA_MODE':'demo','SWING_DB_PATH':'/tmp/swing_server_smoke.db','SWING_HOST':'127.0.0.1','SWING_API_TOKEN':''}
proc=subprocess.Popen([sys.executable,'scripts/launch.py','--port',port],cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
try:
    base='http://127.0.0.1:'+port
    for _ in range(50):
        try:
            status=httpx.get(base+'/health/live',timeout=2)
            if status.status_code==200:break
        except Exception:time.sleep(.1)
    else:raise RuntimeError('Server did not start')
    assert '<!doctype html>' in httpx.get(base,timeout=5).text.lower()
    result=httpx.get(base+'/v1/opportunities',timeout=30).json()
    assert result['total']>0 and result['mode']=='demo'
    assert not result['errors']
    assert all(row['source']=='SYNTHETIC_FIXTURE' for row in result['items'])
    print(f"PASS REAL HTTP server localhost :{port}, {result['total']} synthetic research evaluations")
finally:
    proc.terminate()
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:proc.kill()
