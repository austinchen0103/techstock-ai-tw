from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote
import feedparser
import pandas as pd
import streamlit as st
from analysis_core import TW,US,analyze,macro_data,macro_interpretation
from ai_research import stock_evidence, relevant_news, generate_report

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

news_tab,tw_tab,us_tab,macro_tab,risk_tab,ai_tab=st.tabs(['📰 全球科技新聞','🇹🇼 台股分析','🇺🇸 美股分析','🏦 通膨與台股影響','🧭 風險檢查','🤖 AI 投資研究'])
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

with ai_tab:
    st.subheader('🤖 AI 投資研究｜未來 1～3 個月情境')
    st.caption('只在按下分析按鈕時呼叫 OpenAI API；每次分析可能產生 API 費用。模型無法保證預測準確。')
    api_key = st.secrets.get('OPENAI_API_KEY', '')
    model = st.secrets.get('OPENAI_MODEL', 'gpt-4.1-mini')
    if not api_key:
        st.warning('尚未設定 Streamlit Secrets：OPENAI_API_KEY。其他功能仍可正常使用。')
    symbol = st.text_input('股票代號', value='2330.TW', key='ai_symbol').strip().upper()
    company = st.text_input('公司名稱（改善新聞搜尋）', value='台積電', key='ai_company')
    horizon_risk = st.selectbox('風險承受程度', ['保守', '中等', '積極'], index=1)
    max_loss = st.number_input('可接受的單筆最大損失（%）', min_value=0.5, max_value=30.0, value=5.0, step=0.5)
    st.info('此網站目前為公開網站。請勿輸入帳號密碼、券商帳戶或其他敏感資料；建議限制網站存取權限並設定 API 預算。')
    if st.button('開始 AI 綜合分析（會產生 API 費用）', type='primary', disabled=not bool(api_key), key='run_ai'):
        try:
            with st.spinner('取得歷史行情、新聞與總經資料，並請 AI 分析…'):
                evidence, history = stock_evidence(symbol)
                news = relevant_news(symbol, company)
                macro = get_macro()
                report = generate_report(api_key, model, evidence, news, macro, {'風險程度':horizon_risk, '可接受最大單筆損失%':max_loss})
            st.session_state['ai_report'] = report
            st.session_state['ai_evidence'] = evidence
            st.session_state['ai_history'] = history
            st.session_state['ai_news'] = news
        except Exception as exc:
            st.error(f'分析失敗：{type(exc).__name__}。請檢查 API 金鑰、額度、模型權限與行情資料，或查看 Streamlit Logs。')
    if st.session_state.get('ai_report'):
        evidence = st.session_state['ai_evidence']
        st.caption(f"行情截至：{evidence['資料日期']}｜新聞來源：Google News RSS 標題（未核實全文）")
        st.line_chart(st.session_state['ai_history'], x_label='日期', y_label='調整後收盤價')
        st.markdown(st.session_state['ai_report'])
        st.download_button('下載 AI 研究報告', st.session_state['ai_report'], file_name=f'{evidence["股票代號"]}_ai_research.md', mime='text/markdown')
        with st.expander('本次使用的新聞來源'):
            for n in st.session_state.get('ai_news', []):
                st.markdown(f"- [{n['標題']}]({n['連結']})（{n['發布時間']}）")
