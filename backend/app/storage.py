"""Small SQLite storage with immutable signal snapshots and append-only journal records."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4


def utcnow()->str:return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

class Store:
    def __init__(self,path:Path):
        path.parent.mkdir(parents=True,exist_ok=True)
        self.path=path
        with self.connect() as con:
            con.executescript('''
            CREATE TABLE IF NOT EXISTS runs (
              id TEXT PRIMARY KEY, created_at TEXT NOT NULL, config_json TEXT NOT NULL,
              mode TEXT NOT NULL, result_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS signals (
              id TEXT PRIMARY KEY, run_id TEXT NOT NULL, created_at TEXT NOT NULL, immutable_payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS screeners (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, version INTEGER NOT NULL,
              created_at TEXT NOT NULL, config_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS watchlist (
              instrument_id TEXT PRIMARY KEY, added_at TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '');
            CREATE TABLE IF NOT EXISTS journal (
              id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload_json TEXT NOT NULL);
            ''')
    def connect(self):
        con=sqlite3.connect(self.path,timeout=10)
        con.row_factory=sqlite3.Row
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('PRAGMA busy_timeout=10000')
        return con
    def new_run(self,config:dict,mode:str,result:dict)->str:
        rid='run_'+uuid4().hex[:16]
        with self.connect() as con:
            con.execute('INSERT INTO runs VALUES(?,?,?,?,?)',(rid,utcnow(),json.dumps(config),mode,json.dumps(result)))
            for candidate in result.get('items',[]):
                sid='sig_'+uuid4().hex[:16]
                candidate['signal_id']=sid
                con.execute('INSERT INTO signals VALUES(?,?,?,?)',(sid,rid,utcnow(),json.dumps(candidate)))
            # save enriched run results inside same transaction
            con.execute('UPDATE runs SET result_json=? WHERE id=?',(json.dumps(result),rid))
        return rid
    def latest_run(self)->dict|None:
        with self.connect() as con:
            r=con.execute('SELECT * FROM runs ORDER BY created_at DESC LIMIT 1').fetchone()
        return self.decode_run(r)
    def get_run(self,rid:str)->dict|None:
        with self.connect() as con:r=con.execute('SELECT * FROM runs WHERE id=?',(rid,)).fetchone()
        return self.decode_run(r)
    @staticmethod
    def decode_run(r):
        return {'id':r['id'],'created_at':r['created_at'],'mode':r['mode'],
                'config':json.loads(r['config_json']),'result':json.loads(r['result_json'])} if r else None
    def list_runs(self)->list[dict]:
        with self.connect() as con:r=con.execute('SELECT id,created_at,mode FROM runs ORDER BY created_at DESC LIMIT 50').fetchall()
        return [dict(x) for x in r]
    def signal(self,sid:str)->dict|None:
        with self.connect() as con:r=con.execute('SELECT * FROM signals WHERE id=?',(sid,)).fetchone()
        return {'id':r['id'],'run_id':r['run_id'],'created_at':r['created_at'], 'snapshot':json.loads(r['immutable_payload'])} if r else None
    def list_screeners(self)->list[dict]:
        with self.connect() as con:r=con.execute('SELECT * FROM screeners ORDER BY created_at DESC').fetchall()
        return [dict(x) for x in r]
    def save_screener(self,name:str,config:dict)->dict:
        with self.connect() as con:
            row=con.execute('SELECT max(version) as v FROM screeners WHERE name=?',(name,)).fetchone()
            version=(row['v'] or 0)+1
            item={'id':'scr_'+uuid4().hex[:16],'name':name,'version':version,'created_at':utcnow(),'config_json':json.dumps(config)}
            con.execute('INSERT INTO screeners(id,name,version,created_at,config_json) VALUES(:id,:name,:version,:created_at,:config_json)',item)
            return item
    def watchlist(self)->list[dict]:
        with self.connect() as con:r=con.execute('SELECT * FROM watchlist ORDER BY added_at DESC').fetchall()
        return [dict(x) for x in r]
    def add_watch(self,instrument_id:str,notes:str)->None:
        with self.connect() as con:con.execute('INSERT INTO watchlist VALUES(?,?,?) ON CONFLICT(instrument_id) DO UPDATE SET notes=excluded.notes',(instrument_id,utcnow(),notes))
    def remove_watch(self,instrument_id:str)->None:
        with self.connect() as con:con.execute('DELETE FROM watchlist WHERE instrument_id=?',(instrument_id,))
    def add_trade(self,payload:dict)->dict:
        item={'id':'trade_'+uuid4().hex[:16],'created_at':utcnow(),'payload':payload}
        with self.connect() as con:con.execute('INSERT INTO journal VALUES(?,?,?)',(item['id'],item['created_at'],json.dumps(payload)))
        return item
    def journal(self)->list[dict]:
        with self.connect() as con:r=con.execute('SELECT * FROM journal ORDER BY created_at DESC').fetchall()
        return [{'id':x['id'],'created_at':x['created_at'],**json.loads(x['payload_json'])} for x in r]
