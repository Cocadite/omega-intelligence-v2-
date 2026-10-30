import asyncio, time, math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app=FastAPI(title="OMEGA Intelligence V2")
CACHE={"at":0,"data":None}
FETCH_LOCK=asyncio.Lock()
ASSETS=[("BTC","crypto","BTCUSDT"),("ETH","crypto","ETHUSDT"),("SOL","crypto","SOLUSDT"),("BNB","crypto","BNBUSDT"),("XRP","crypto","XRPUSDT"),("ADA","crypto","ADAUSDT"),("EURUSD","forex","EURUSD=X"),("GBPUSD","forex","GBPUSD=X"),("USDJPY","forex","JPY=X"),("USDCHF","forex","CHF=X"),("AUDUSD","forex","AUDUSD=X"),("USDCAD","forex","CAD=X"),("EURGBP","forex","EURGBP=X"),("AAPL","stocks","AAPL"),("MSFT","stocks","MSFT"),("NVDA","stocks","NVDA"),("GOOGL","stocks","GOOGL"),("AMZN","stocks","AMZN"),("META","stocks","META"),("TSLA","stocks","TSLA"),("SPY","stocks","SPY")]

def status(group):
    now=datetime.now(timezone.utc)
    if group=="crypto": return "24/7"
    if group=="forex": return "Aberto" if (now.weekday()<4 or now.weekday()==4 and now.hour<22 or now.weekday()==6 and now.hour>=22) else "Fechado"
    ny=now.astimezone(ZoneInfo("America/New_York"))
    return "Aberto" if ny.weekday()<5 and 9*60+30<=ny.hour*60+ny.minute<16*60 else "Fechado"

def indicators(values):
    if len(values)<20:return {"trend":"Dados insuficientes","change":None,"volatility":None,"sma20":None}
    last=values[-1]; old=values[-2]
    ret=[(values[i]/values[i-1]-1)*100 for i in range(1,len(values)) if values[i-1]>0]
    mean=sum(ret)/len(ret)
    vol=math.sqrt(sum((r-mean)**2 for r in ret)/len(ret))
    sma=sum(values[-20:])/20
    return {"trend":"Acima da média" if last>sma else "Abaixo da média","change":round((last/old-1)*100,3),"volatility":round(vol,3),"sma20":round(sma,5)}

async def load_one(client,item):
    symbol,group,ticker=item
    try:
        if group=="crypto":
            errors=[]
            for host in ("data-api.binance.vision","api.binance.com"):
                try:
                    r=await client.get("https://"+host+"/api/v3/klines",params={"symbol":ticker,"interval":"1h","limit":80})
                    r.raise_for_status()
                    break
                except Exception as e:
                    errors.append(str(e))
            else:
                raise ValueError("Crypto indisponível: "+"; ".join(errors)[:100])
            payload=r.json()
            if not isinstance(payload,list) or len(payload)<20:
                raise ValueError("Resposta inválida da Binance")
            values=[float(x[4]) for x in payload]
            source="Binance Spot • candles 1h"
        else:
            errors=[]
            for host in ("query1.finance.yahoo.com","query2.finance.yahoo.com"):
                try:
                    r=await client.get(f"https://{host}/v8/finance/chart/{ticker}",params={"range":"3mo","interval":"1d"},headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
                    r.raise_for_status()
                    break
                except Exception as e:
                    errors.append(str(e))
            else:
                raise ValueError("Yahoo indisponível: "+"; ".join(errors)[:100])
            result=r.json()["chart"]["result"][0]
            values=[float(v) for v in result["indicators"]["quote"][0]["close"] if v is not None]
            source="Yahoo Finance • candles 1d"
        if not values:raise ValueError("Sem preços")
        return {"symbol":symbol,"group":group,"status":status(group),"price":round(values[-1],5),"source":source,"analysis":indicators(values),"history":[round(x,5) for x in values[-35:]],"error":None}
    except Exception as exc:
        return {"symbol":symbol,"group":group,"status":status(group),"price":None,"source":None,"analysis":None,"history":[],"error":str(exc)[:120]}

@app.get("/api/markets")
async def markets():
    if CACHE["data"] is not None and time.time()-CACHE["at"]<60:return CACHE["data"]
    async with httpx.AsyncClient(timeout=15,follow_redirects=True,limits=httpx.Limits(max_connections=12)) as client:
        rows=await asyncio.gather(*(load_one(client,item) for item in ASSETS))
    result={"updated_at":datetime.now(timezone.utc).isoformat(),"refresh_seconds":60,"assets":rows,"disclaimer":"Análise estatística experimental; não são recomendações financeiras. Horários aproximados, sem feriados."}
    CACHE.update(at=time.time(),data=result)
    return result

@app.get("/health")
def health():return {"ok":True}

@app.get("/",response_class=HTMLResponse)
def home():
    return HTML
HTML='''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OMEGA Intelligence V2</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#070e13;color:#e8f9f2;font:14px system-ui,Arial}header{display:flex;justify-content:space-between;align-items:center;padding:22px 4%;border-bottom:1px solid #1a3530;background:#0b161a}h1{font-size:21px;margin:0;letter-spacing:1px}h1 span{color:#39f6a4}.sub{color:#8aaba3;font-size:12px}main{max-width:1400px;margin:auto;padding:25px 4%}.stats,.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px}.card{background:#101e23;border:1px solid #244039;border-radius:15px;padding:18px;min-width:0}.big{font-size:26px;font-weight:700;margin:8px 0;color:#e7fff4}.green{color:#39f6a4}.muted{color:#8aaba3}h2{font-size:16px;margin:28px 0 13px}.row{display:flex;justify-content:space-between;gap:8px;align-items:center}.tag{font-size:11px;border:1px solid #386e58;padding:4px 8px;border-radius:20px;color:#39f6a4}.bad{color:#ff9c9c}.price{font-size:25px;font-weight:700;margin:14px 0 7px}.line{height:1px;background:#264039;margin:13px 0}.small{font-size:12px;line-height:1.8}.note{padding:14px;border:1px solid #355148;border-radius:12px;color:#a9c7bc;margin-top:20px}.buttons{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}.buttons button{background:#112d28;color:#a8dfca;border:1px solid #286047;border-radius:8px;padding:9px 16px;cursor:pointer}.buttons button.active{background:#21ad73;color:#06150f}.spark{width:100%;height:56px;margin:9px 0}#message{color:#9ebbb0}@media(max-width:750px){.stats,.grid{grid-template-columns:1fr}h1{font-size:17px}main{padding:18px 4%}}
</style></head><body><header><div><h1>◈ OMEGA <span>INTELLIGENCE</span></h1><div class="sub">MARKET RESEARCH TERMINAL · V2</div></div><div class="tag">● ANÁLISE EXPERIMENTAL</div></header><main><div class="row"><div><h2>Visão geral dos mercados</h2><div class="sub" id="updated">Carregando dados...</div></div><div class="tag">↻ 60 SEGUNDOS</div></div><section class="stats"><div class="card"><div class="muted">CRYPTO</div><div class="big green">24/7</div><div class="small muted">Mercado contínuo</div></div><div class="card"><div class="muted">FOREX</div><div class="big" id="fx">—</div><div class="small muted">Horário aproximado</div></div><div class="card"><div class="muted">STOCKS (EUA)</div><div class="big" id="stocks">—</div><div class="small muted">Sessão regular; sem feriados</div></div></section><h2>Radar multiativos · 20 instrumentos</h2><div class="buttons"><button class="active" data-filter="all">Todos</button><button data-filter="crypto">Crypto</button><button data-filter="forex">Forex</button><button data-filter="stocks">Stocks</button></div><div id="message"></div><section id="grid" class="grid"></section><h2>OMEGA Strategy Lab</h2><div class="card"><div class="row"><b>Estudo estatístico descritivo</b><span class="tag">SEM ORDENS</span></div><p class="muted">A média móvel de 20 períodos, a variação entre candles e a volatilidade são calculadas para comparar comportamentos históricos. Não existe aqui um modelo treinado, previsão validada ou recomendação de compra/venda.</p></div><div class="note">⚠ Dados externos podem apresentar atraso ou indisponibilidade. Status de bolsas é aproximado e não considera feriados. Nenhum saldo, carteira, corretora ou operação é utilizado.</div></main><script>
let filter='all',rows=[];const $=x=>document.getElementById(x);
function spark(values){if(values.length<2)return '';let lo=Math.min(...values),hi=Math.max(...values),d=hi-lo||1;let points=values.map((v,i)=>(i*300/(values.length-1)).toFixed(1)+','+(52-(v-lo)*46/d).toFixed(1)).join(' ');return '<svg class="spark" viewBox="0 0 300 56" preserveAspectRatio="none"><polyline points="'+points+'" fill="none" stroke="#39f6a4" stroke-width="2"/></svg>'}
function render(){let filtered=rows.filter(x=>filter==='all'||x.group===filter);$('grid').innerHTML=filtered.map(x=>{let a=x.analysis;return '<article class="card"><div class="row"><b>'+x.symbol+'</b><span class="tag">'+x.group.toUpperCase()+'</span></div><div class="price">'+(x.price===null?'Indisponível':x.price.toLocaleString('pt-BR',{maximumFractionDigits:5}))+'</div>'+spark(x.history)+'<div class="line"></div><div class="small"><div class="row"><span class="muted">Tendência vs SMA20</span><b>'+(a?a.trend:'—')+'</b></div><div class="row"><span class="muted">Variação do candle</span><b>'+(a&&a.change!==null?a.change+'%':'—')+'</b></div><div class="row"><span class="muted">Volatilidade histórica</span><b>'+(a&&a.volatility!==null?a.volatility+'%':'—')+'</b></div><div class="row"><span class="muted">Fonte</span><span>'+(x.source||'Falha na fonte')+'</span></div></div></article>'}).join('')}
document.querySelectorAll('button[data-filter]').forEach(b=>b.onclick=()=>{filter=b.dataset.filter;document.querySelectorAll('button[data-filter]').forEach(z=>z.classList.toggle('active',z===b));render()});
async function refresh(){try{let r=await fetch('/api/markets');if(!r.ok)throw Error('HTTP '+r.status);let d=await r.json();rows=d.assets;$('updated').textContent='Última coleta: '+new Date(d.updated_at).toLocaleString('pt-BR');$('fx').textContent=rows.find(x=>x.group==='forex').status;$('stocks').textContent=rows.find(x=>x.group==='stocks').status;$('message').textContent=rows.filter(x=>x.error).length+' de '+rows.length+' ativos sem dados nesta atualização.';render()}catch(e){$('message').textContent='Não foi possível atualizar: '+e.message}}
refresh();setInterval(refresh,60000);
</script></body></html>'''
