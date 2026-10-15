from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote
import feedparser
import pandas as pd
import streamlit as st
from analysis_core import TW,US,analyze,macro_data,macro_interpretation

TZ=ZoneInfo('Asia/Taipei')
st.set_page_config(page_title='TechStock AI｜台美股與通膨研究',page_icon='📈',layout='wide')
st.title('📈 TechStock AI｜台美股與通膨研究助理')
st.caption('台股 × 美股 × 美國通膨與利率。資料可能延遲；非投資建議或自動交易。')
with st.sidebar:
    period=st.selectbox('技術分析區間',['1mo','3mo','6mo'],index=1)
    tw_raw=st.text_area('台股自選（代號,名稱）','\n'.join(f'{k},{v}' for k,v in TW.items()),height=160)
    us_raw=st.text_area('美股自選（代號,名稱）','\n'.join(f'{k},{v}' for k,v in US.items()),height=160)

def parse(raw):
    result=[]
    for line in raw.splitlines():
        if line.strip():
            parts=line.split(',',1);symbol=parts[0].strip().upper()
            if symbol:result.append((symbol,parts[1].strip() if len(parts)>1 else symbol))
    return result

@st.cache_data(ttl=300,show_spinner=False)
def stock_rows(items,period):return [analyze(t,n,period) for t,n in items]

@st.cache_data(ttl=3600,show_spinner=False)
def get_macro():return macro_data()

@st.cache_data(ttl=900,show_spinner=False)
def get_news():
    out=[];seen=set()
    for term in ('台灣 半導體 AI 科技','美股 NVIDIA NASDAQ inflation','美國 CPI PCE 聯準會 利率'):
        url='https://news.google.com/rss/search?q='+quote(term)+'&hl=zh-TW&gl=TW&ceid=TW:zh-Hant'
        try:
            for e in feedparser.parse(url).entries:
                title=e.get('title','');link=e.get('link','')
                if title and link and link not in seen:
                    seen.add(link);out.append((title,link,e.get('published','時間未提供'),term))
        except Exception:pass
    return out[:30]

def stock_panel(raw,market):
    if st.button(f'更新{market}行情',key=market):stock_rows.clear()
    with st.spinner('讀取行情中…'):rows=stock_rows(tuple(parse(raw)),period)
    if not rows:st.warning('請先輸入自選股');return
    df=pd.DataFrame(rows)
    st.dataframe(df,use_container_width=True,hide_index=True)
    st.download_button('下載分析 CSV',df.to_csv(index=False).encode('utf-8-sig'),f'{market}_analysis.csv','text/csv',key='dl_'+market)
    st.caption('研究分數僅依 MA5、MA20 與成交量計算，並未經回測；美股幣別通常為美元，台股通常為新台幣。')

news_tab,tw_tab,us_tab,macro_tab,risk_tab=st.tabs(['📰 全球科技新聞','🇹🇼 台股分析','🇺🇸 美股分析','🏦 通膨與台股影響','🧭 風險檢查'])
with news_tab:
    if st.button('重新整理新聞'):get_news.clear()
    for title,link,published,term in get_news():
        with st.container(border=True):
            st.markdown(f'**[{title}]({link})**');st.caption(f'{term} · {published}')
with tw_tab:stock_panel(tw_raw,'台股')
with us_tab:stock_panel(us_raw,'美股')
with macro_tab:
    st.subheader('美國通膨與利率指標（FRED）')
    if st.button('更新總經資料'):get_macro.clear()
    with st.spinner('讀取 FRED 資料中…'):rows=get_macro()
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    st.caption('CPI、PCE 為指數相對12個月前的年增率；利率與殖利率為原始百分比。觀測期間不是發布日期，FRED 資料可能修訂。')
    st.subheader('對美股與台灣科技股的可能影響')
    for note in macro_interpretation(rows):st.write('• '+note)
    st.markdown('[資料來源：FRED（聖路易聯邦準備銀行）](https://fred.stlouisfed.org/)')
with risk_tab:
    st.subheader('交易前風險檢查')
    for i,s in enumerate(['確認新聞與經濟數據的發布時間','確認台美股行情日期、幣別與延遲','確認通膨公布值與市場預期是否不同','設定停損與可承受最大損失','考慮匯率、交易成本、滑價及流動性','不單憑模型評分或新聞下單']):st.checkbox(s,key=f'risk_{i}')
    capital=st.number_input('交易資金（以所選幣別計）',min_value=0,value=100000,step=10000)
    risk=st.slider('單筆風險預算（%）',0.1,2.0,0.5,0.1)
    entry=st.number_input('預計進場價',min_value=0.0,value=100.0)
    stop=st.number_input('假設停損價',min_value=0.0,value=97.0)
    if entry>stop>0:
        shares=int((capital*risk/100)//(entry-stop))
        st.metric('依風險預算估算股數',f'{shares:,} 股')
        st.caption('僅依價格差估算，未計入手續費、交易稅、匯差、滑價、跳空；不是買進建議。')
    else:st.warning('停損價必須大於0且低於進場價')
st.divider();st.caption('頁面產生時間：'+datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')+' 台灣時間')
