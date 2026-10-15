from io import StringIO
from urllib.request import Request, urlopen
import pandas as pd
import yfinance as yf

TW = {'2330.TW':'台積電','2454.TW':'聯發科','2317.TW':'鴻海','2382.TW':'廣達','2308.TW':'台達電','3711.TW':'日月光投控'}
US = {'NVDA':'NVIDIA','AMD':'AMD','AAPL':'Apple','MSFT':'Microsoft','GOOGL':'Alphabet','TSLA':'Tesla','TSM':'台積電 ADR','AVGO':'Broadcom','QQQ':'NASDAQ-100 ETF','SPY':'S&P 500 ETF','SOXX':'半導體 ETF'}
FRED = {'CPIAUCSL':('美國 CPI','年增率 %'),'CPILFESL':('美國核心 CPI','年增率 %'),'PCEPI':('美國 PCE 物價指數','年增率 %'),'PCEPILFE':('美國核心 PCE','年增率 %'),'FEDFUNDS':('聯邦基金有效利率','%'),'DGS10':('美國10年期公債殖利率','%')}

def analyze(ticker,name,period='3mo'):
    try:
        hist=yf.Ticker(ticker).history(period=period,auto_adjust=False)
        if hist is None or hist.empty:return {'代號':ticker,'名稱':name,'狀態':'沒有行情'}
        close=hist['Close'].dropna();volume=hist['Volume'].reindex(close.index).fillna(0)
        if len(close)<20:return {'代號':ticker,'名稱':name,'狀態':'不足20個交易日資料'}
        last=float(close.iloc[-1]);prev=float(close.iloc[-2]);ma5=float(close.tail(5).mean());ma20=float(close.tail(20).mean())
        pct=(last/prev-1)*100 if prev else 0
        avgvol=float(volume.tail(20).mean());vr=float(volume.iloc[-1])/avgvol if avgvol else 0
        score=(1 if last>ma5 else -1)+(1 if ma5>ma20 else -1)
        if vr>=1.5:score+=1 if pct>0 else (-1 if pct<0 else 0)
        label='偏多觀察' if score>=2 else ('偏空／觀望' if score<=-1 else '中性觀察')
        return {'代號':ticker,'名稱':name,'資料日期':str(close.index[-1].date()),'收盤價':round(last,2),'單日變動%':round(pct,2),'MA5':round(ma5,2),'MA20':round(ma20,2),'量比':round(vr,2),'研究分數':score,'分類':label,'狀態':'正常'}
    except Exception as e:return {'代號':ticker,'名稱':name,'狀態':f'讀取失敗：{type(e).__name__}'}

def macro_data():
    rows=[]
    for series,(label,unit) in FRED.items():
        try:
            url=f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}'
            req=Request(url,headers={'User-Agent':'Mozilla/5.0'})
            with urlopen(req,timeout=12) as res: df=pd.read_csv(StringIO(res.read().decode('utf-8')))
            df.columns=['date','value'];df['date']=pd.to_datetime(df['date']);df['value']=pd.to_numeric(df['value'],errors='coerce')
            df=df.dropna().sort_values('date')
            if series in ('CPIAUCSL','CPILFESL','PCEPI','PCEPILFE'):
                df['metric']=df['value'].pct_change(12)*100
            else:df['metric']=df['value']
            df=df.dropna(subset=['metric'])
            if df.empty:raise ValueError('no observations')
            latest=df.iloc[-1]
            rows.append({'指標':label,'數值':round(float(latest['metric']),2),'單位':unit,'觀測期間':latest['date'].strftime('%Y-%m-%d'),'狀態':'正常'})
        except Exception as e:rows.append({'指標':label,'數值':None,'單位':unit,'觀測期間':'—','狀態':f'暫無資料 ({type(e).__name__})'})
    return rows

def macro_interpretation(rows):
    data={r['指標']:r['數值'] for r in rows if r['狀態']=='正常'}
    notes=['以下為一般經濟傳導情境，並非由 CPI 單獨預測股價；通膨數值為已公布歷史觀測值，不是市場預期差。']
    cpi=data.get('美國核心 CPI');pce=data.get('美國核心 PCE')
    if cpi is not None:
        notes.append(f'核心 CPI 年增 {cpi:.2f}%。通膨黏著可能使降息預期延後，對高估值科技股形成壓力；若持續降溫則可能緩和利率壓力。')
    if pce is not None:notes.append(f'核心 PCE 年增 {pce:.2f}%。聯準會重視 PCE，但政策還取決於就業、成長與金融條件。')
    if '美國10年期公債殖利率' in data:notes.append(f'10年期美債殖利率為 {data["美國10年期公債殖利率"]:.2f}%，殖利率上升通常提高成長股折現率，但並非必然導致下跌。')
    notes.append('對台股：觀察 NASDAQ、半導體 ETF、台積電 ADR 與新台幣匯率；AI 需求、財報、地緣政治也可能主導走勢。')
    notes.append('重要限制：FRED 的觀測期間不等於正式發布日；本系統未接入市場預期值，無法判斷「高於／低於預期」。')
    return notes
