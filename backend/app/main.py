"""Private API and packaged responsive web client."""
from __future__ import annotations
import hmac
from decimal import Decimal,InvalidOperation
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI,HTTPException,Request,Query,Header
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from .config import settings
from .history_api import router as history_router
from .domain import position_size
from .registry import get_instruments
from .universe import snapshot_metadata
from .providers import load_bars,ProviderError
from .backtest import replay
from .rules import ScreenerConfig,validate_rules,RuleError
from .service import scan,get_latest
from .storage import Store

app=FastAPI(title='Personal Swing Intelligence',version='0.3.0',docs_url='/api-docs',redoc_url=None)
app.include_router(history_router)
store=Store(settings.db_path)
WEB=Path(__file__).resolve().parents[2]/'web'
app.mount('/static',StaticFiles(directory=str(WEB)),name='static')

@app.middleware('http')
async def private_guard(request:Request,call_next):
    path=request.url.path
    # Static app and minimal health may load without auth, API is always guarded if configured.
    if (path.startswith('/v1/') or path=='/health/ready' or path.startswith('/api-docs') or path.startswith('/openapi')) and settings.api_token:
        raw=request.headers.get('authorization','')
        expected='Bearer '+settings.api_token
        if not hmac.compare_digest(raw,expected):
            return JSONResponse({'detail':'Authentication required'},status_code=401)
    if path.startswith('/v1/') and request.method in ('POST','PUT','PATCH'):
        if int(request.headers.get('content-length','0') or '0')>50000:
            return JSONResponse({'detail':'Request exceeds 50 KB'},status_code=413)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Cache-Control']='no-store' if path.startswith('/v1') else 'private, max-age=0'
    response.headers['X-Request-ID']=uuid4().hex
    return response

@app.get('/')
def home():return FileResponse(WEB/'index.html')

@app.get('/health/live')
def live():return {'status':'ok','version':'0.3.0','mode':settings.data_mode}

@app.get('/health/ready')
def ready():return {'status':'ok','database':store.path.exists(),'provider_mode':settings.data_mode}

@app.get('/v1/meta')
def meta():return {'version':'0.3.0','mode':settings.data_mode,'private':True,
                   'forecasts':'NOT_VALIDATED','order_execution':'DISABLED',
                   'execution_checks':'UNVERIFIED', 'supported_markets':['US','IDX','CRYPTO'],
                   'source_notice':'Demo means 100% synthetic data; LIVE uses external feeds and can fail.'}

@app.get('/v1/instruments')
def instruments(search:str='',market:str='ALL'):
    return {'items':[i.__dict__ for i in get_instruments(settings.data_mode) if (market=='ALL' or i.market==market) and
                     (search.lower() in i.symbol.lower() or search.lower() in i.name.lower())]}

@app.get('/v1/opportunities')
def opportunities(market:str='ALL',strategy:str='BOTH',min_score:int=Query(0,ge=0,le=100),
                  included_only:bool=False,search:str=''):
    if market not in ('ALL','US','IDX','CRYPTO'):raise HTTPException(422,'Invalid market')
    if strategy not in ('BOTH','PULLBACK','BREAKOUT'):raise HTTPException(422,'Invalid strategy')
    result=get_latest(store,settings.data_mode)
    items=[x for x in result['items'] if (market=='ALL' or x['market']==market) and
           (strategy=='BOTH' or x['setup']['strategy']==strategy) and x['setup']['score']>=min_score
           and (not included_only or x['liquidity']['historical']=='PASS') and
           (search.lower() in x['symbol'].lower() or search.lower() in x['name'].lower())]
    return {'run_id':result['run_id'],'generated_at':result['generated_at'],
            'mode':settings.data_mode,'total':len(items),'items':items,
            'errors':result['errors'],'exclusions':result['exclusions'],
            'coverage':result.get('coverage', {}),
            'forecast_status':'NOT_VALIDATED'}

@app.get('/v1/universe')
def universe():
    result=get_latest(store,settings.data_mode)
    return {'mode':settings.data_mode,'run_id':result['run_id'],'instruments':len(get_instruments(settings.data_mode)),
            'excluded':result['exclusions'],'provider_errors':result['errors']}


@app.get('/v1/universe/discovery')
def universe_discovery():
    return {'mode': settings.data_mode, 'registry_count':len(get_instruments(settings.data_mode)),
            **snapshot_metadata()}

@app.get('/v1/instruments/{instrument_id:path}/analysis')
def analysis(instrument_id:str):
    result=get_latest(store,settings.data_mode)
    options=[x for x in result['items'] if x['instrument_id']==instrument_id]
    if not options:raise HTTPException(404,'No cached analysis for instrument. Run scan with BOTH strategies.')
    return {'instrument_id':instrument_id,'mode':settings.data_mode,'analyses':options,'run_id':result['run_id']}

@app.post('/v1/screeners/validate')
def validate(body:ScreenerConfig):return {'valid':True,'config':body.model_dump(),'nodes':validate_rules(body.rules)}

@app.post('/v1/screeners')
def save_screener(body:ScreenerConfig):
    return store.save_screener(body.name,body.model_dump())

@app.get('/v1/screeners')
def list_screeners():return {'items':store.list_screeners()}

@app.post('/v1/screeners/runs')
def run_screener(body:ScreenerConfig):
    return scan(store,settings.data_mode,body)

@app.get('/v1/screeners/runs')
def runs():return {'items':store.list_runs()}

@app.get('/v1/screeners/runs/{run_id}')
def get_run(run_id:str):
    result=store.get_run(run_id)
    if not result:raise HTTPException(404,'Run not found')
    return result

@app.get('/v1/signals/{signal_id}')
def signal(signal_id:str):
    data=store.signal(signal_id)
    if data is None:raise HTTPException(404,'Signal not found')
    return data

class WatchRequest(BaseModel):
    instrument_id:str=Field(min_length=5,max_length=120)
    notes:str=Field(default='',max_length=500)

@app.get('/v1/watchlist')
def watchlist():return {'items':store.watchlist()}

@app.post('/v1/watchlist')
def add_watch(body:WatchRequest):
    if body.instrument_id not in {i.instrument_id for i in get_instruments(settings.data_mode)}:raise HTTPException(422,'Unknown instrument')
    store.add_watch(body.instrument_id,body.notes)
    return {'ok':True}

@app.delete('/v1/watchlist/{instrument_id:path}')
def remove_watch(instrument_id:str):
    store.remove_watch(instrument_id)
    return {'ok':True}

class TradeRequest(BaseModel):
    instrument_id:str=Field(min_length=5,max_length=120)
    side:str='LONG'
    mode:str='PAPER'
    entry:Decimal=Field(gt=0)
    quantity:Decimal=Field(gt=0)
    stop:Decimal|None=None
    exit:Decimal|None=None
    fees:Decimal=Field(default=Decimal('0'),ge=0)
    notes:str=Field(default='',max_length=1000)
    signal_id:str|None=None

@app.get('/v1/journal/trades')
def journal():return {'items':store.journal()}

@app.post('/v1/journal/trades')
def add_trade(body:TradeRequest):
    if body.side!='LONG' or body.mode not in ('PAPER','MANUAL'):
        raise HTTPException(422,'Only paper/manual long-only trades supported')
    if body.instrument_id not in {i.instrument_id for i in get_instruments(settings.data_mode)}:
        raise HTTPException(422,'Unknown instrument')
    if body.stop is not None and not 0<body.stop<body.entry:raise HTTPException(422,'Stop must be below entry')
    if body.exit is not None and body.exit<=0:raise HTTPException(422,'Invalid exit')
    payload=body.model_dump(mode='json')
    if body.exit is not None:
        payload['realized_pnl']=str((body.exit-body.entry)*body.quantity-body.fees)
    return store.add_trade(payload)

class SizeRequest(BaseModel):
    capital:Decimal
    entry:Decimal
    stop:Decimal
    risk_pct:Decimal=Decimal('0.5')
    market:str='IDX'
    max_position_pct:Decimal=Decimal('20')
    fee_pct:Decimal=Decimal('0')

@app.post('/v1/risk/size')
def size(body:SizeRequest):
    try:return position_size(body.capital,body.entry,body.stop,body.risk_pct,
                             body.market,body.max_position_pct,body.fee_pct)
    except (ValueError,InvalidOperation) as exc:raise HTTPException(422,str(exc)) from exc

@app.get('/v1/backtests/{instrument_id:path}')
def backtest(instrument_id:str,strategy:str='PULLBACK',horizon:int=10):
    if strategy not in ('PULLBACK','BREAKOUT'):raise HTTPException(422,'Invalid strategy')
    ins=next((i for i in get_instruments(settings.data_mode) if i.instrument_id==instrument_id),None)
    if ins is None:raise HTTPException(404,'Unknown instrument')
    try:
        bars,_,_,_=load_bars(ins,settings.data_mode)
        return replay(ins,bars,strategy,horizon)
    except (ProviderError,ValueError) as exc:raise HTTPException(503,str(exc)) from exc

@app.get('/v1/forecast/{instrument_id:path}')
def forecast(instrument_id:str):
    return {'instrument_id':instrument_id,'status':'NOT_VALIDATED','probabilities':None,
            'price_distribution':None,'reason':'Not enough OOS research evidence to publish forecasts.'}
