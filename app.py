import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import yfinance as yf
import feedparser

TZ = ZoneInfo("Asia/Taipei")
DEFAULT_WATCHLIST = {
    "2330.TW": "台積電",
    "2454.TW": "聯發科",
    "2317.TW": "鴻海",
    "2382.TW": "廣達",
    "2308.TW": "台達電",
    "3711.TW": "日月光投控",
}
NEWS_FEEDS = [
    ("Google News｜台灣科技", "https://news.google.com/rss/search?q=台灣+科技+半導體+AI&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
    ("Google News｜台股電子", "https://news.google.com/rss/search?q=台股+電子股+半導體+伺服器&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
    ("Google News｜AI 供應鏈", "https://news.google.com/rss/search?q=AI+伺服器+GPU+HBM+台灣供應鏈&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
]

st.set_page_config(page_title="TechStock AI｜台股研究助理", page_icon="📈", layout="wide")
st.title("📈 TechStock AI｜台股短線研究助理")
st.caption("科技新聞 × 台股觀察 × 技術指標。研究輔助工具，非即時下單或保證獲利系統。")

with st.sidebar:
    st.header("設定")
    st.write("市場：台股｜時區：Asia/Taipei")
    watchlist_text = st.text_area(
        "自選股（每行：代號,名稱）",
        value="\n".join(f"{k},{v}" for k, v in DEFAULT_WATCHLIST.items()),
        height=180,
    )
    period = st.selectbox("技術分析區間", ["1mo", "3mo", "6mo"], index=1)
    st.caption("台股代號使用 Yahoo Finance 格式，例如 2330.TW；上櫃股票常用 .TWO。")

def parse_watchlist(raw):
    items = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split(",", 1)]
        ticker = parts[0].upper()
        name = parts[1] if len(parts) > 1 else ticker
        if ticker:
            items.append((ticker, name))
    return items

def get_news(limit=20):
    entries = []
    seen = set()
    for source, url in NEWS_FEEDS:
        try:
            parsed = feedparser.parse(url)
            for e in parsed.entries:
                title = getattr(e, "title", "").strip()
                link = getattr(e, "link", "")
                key = (title, link)
                if not title or key in seen:
                    continue
                seen.add(key)
                entries.append({
                    "新聞標題": title,
                    "來源分類": source,
                    "發布時間": getattr(e, "published", "時間未提供"),
                    "連結": link,
                    "摘要": getattr(e, "summary", "")[:500],
                })
        except Exception:
            continue
    return entries[:limit]

def analyze_ticker(ticker, name, period="3mo"):
    try:
        hist = yf.Ticker(ticker).history(period=period, auto_adjust=False)
        if hist is None or hist.empty or len(hist) < 5:
            return {"代號": ticker, "名稱": name, "狀態": "無足夠行情資料"}
        close = hist["Close"].dropna()
        volume = hist["Volume"].fillna(0)
        last = float(close.iloc[-1])
        prev = float(close.iloc[-2])
        day_pct = (last / prev - 1) * 100 if prev else 0
        ma5 = float(close.tail(5).mean())
        ma20 = float(close.tail(20).mean()) if len(close) >= 20 else float(close.mean())
        avg_vol20 = float(volume.tail(20).mean()) if len(volume) >= 20 else float(volume.mean())
        latest_vol = float(volume.iloc[-1])
        vol_ratio = latest_vol / avg_vol20 if avg_vol20 else 0
        ret5 = (last / float(close.iloc[-6]) - 1) * 100 if len(close) >= 6 and close.iloc[-6] else 0
        score = 0
        reasons = []
        if last > ma5:
            score += 1
            reasons.append("收盤價高於 5 日均線")
        else:
            score -= 1
            reasons.append("收盤價低於 5 日均線")
        if ma5 > ma20:
            score += 1
            reasons.append("5 日均線高於 20 日均線")
        else:
            score -= 1
            reasons.append("5 日均線未高於 20 日均線")
        if vol_ratio >= 1.5 and day_pct > 0:
            score += 1
            reasons.append("上漲且成交量高於近 20 日均量 1.5 倍")
        elif vol_ratio >= 1.5 and day_pct < 0:
            score -= 1
            reasons.append("下跌且成交量放大，留意賣壓")
        if day_pct >= 7:
            reasons.append("單日漲幅偏大，避免盲目追價")
        if day_pct <= -5:
            reasons.append("單日跌幅偏大，檢查是否有重大利空")
        label = "偏多觀察" if score >= 2 else ("偏空／觀望" if score <= -1 else "中性觀察")
        return {
            "代號": ticker, "名稱": name, "資料日期": str(hist.index[-1].date()),
            "收盤價": round(last, 2), "單日變動%": round(day_pct, 2),
            "近 5 日變動%": round(ret5, 2), "MA5": round(ma5, 2),
            "MA20": round(ma20, 2), "成交量/20日均量": round(vol_ratio, 2),
            "研究分數": score, "觀察分類": label, "判讀依據": "；".join(reasons),
            "狀態": "正常"
        }
    except Exception as ex:
        return {"代號": ticker, "名稱": name, "狀態": f"資料讀取失敗：{type(ex).__name__}"}

st.info("行情可能延遲或缺漏。請先確認資料日期；盤中數值不可視為交易所即時報價。")
tab1, tab2, tab3 = st.tabs(["📰 科技新聞", "📊 台股觀察清單", "🧭 交易風險檢查"])

with tab1:
    st.subheader("近期科技新聞")
    if st.button("重新整理新聞", key="refresh_news"):
        st.cache_data.clear()
    @st.cache_data(ttl=900, show_spinner=False)
    def cached_news():
        return get_news(30)
    news = cached_news()
    if not news:
        st.warning("目前無法取得 RSS 新聞，請稍後重試或檢查網路。")
    for item in news:
        with st.container(border=True):
            st.markdown(f"**[{item['新聞標題']}]({item['連結']})**")
            st.caption(f"{item['來源分類']} · {item['發布時間']}")
            if item["摘要"]:
                st.write(item["摘要"], unsafe_allow_html=False)
    st.caption("新聞由 Google News RSS 搜尋結果彙整；請點入原文核實內容與發布時間。")

with tab2:
    st.subheader("自選股技術指標")
    watchlist = parse_watchlist(watchlist_text)
    if st.button("更新行情與指標", type="primary"):
        st.cache_data.clear()
    @st.cache_data(ttl=300, show_spinner=False)
    def cached_analysis(items, selected_period):
        return [analyze_ticker(t, n, selected_period) for t, n in items]
    with st.spinner("正在讀取行情資料…"):
        rows = cached_analysis(tuple(watchlist), period)
    if rows:
        df = pd.DataFrame(rows)
        if "研究分數" in df.columns:
            cols = [c for c in ["代號", "名稱", "資料日期", "收盤價", "單日變動%", "近 5 日變動%", "MA5", "MA20", "成交量/20日均量", "研究分數", "觀察分類", "狀態"] if c in df.columns]
            st.dataframe(df[cols], use_container_width=True, hide_index=True)
            for row in rows:
                if row.get("狀態") == "正常":
                    with st.expander(f"{row['代號']} {row['名稱']}｜{row['觀察分類']}"):
                        st.write("**判讀依據：**", row["判讀依據"])
                        st.write("**注意：** 技術指標只反映歷史價格與成交量，不包含未公開資訊，也不保證未來走勢。")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("下載分析 CSV", data=pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig"),
                       file_name="techstock_watchlist.csv", mime="text/csv")

with tab3:
    st.subheader("下單前風險檢查")
    st.write("每筆交易前，請自行確認以下事項。")
    checks = [
        "已閱讀原始新聞，確認發布時間與消息來源。",
        "已確認行情資料日期、交易狀態及是否為延遲報價。",
        "已設定可承受的最大損失與停損條件。",
        "部位大小符合風險預算，沒有因單一新聞過度集中。",
        "已考慮交易成本、滑價、流動性與漲跌幅限制。",
        "沒有只因 AI 分數或社群傳言就追價。",
    ]
    for c in checks:
        st.checkbox(c, key="risk_" + str(checks.index(c)))
    st.markdown("**簡易部位估算**")
    capital = st.number_input("可用交易資金（新台幣）", min_value=0, value=100000, step=10000)
    risk_pct = st.slider("單筆最大風險預算（資金百分比）", 0.1, 2.0, 0.5, 0.1)
    entry = st.number_input("預計進場價（元）", min_value=0.0, value=100.0, step=1.0)
    stop = st.number_input("假設停損價（元）", min_value=0.0, value=97.0, step=0.5)
    if entry > stop > 0:
        risk_cash = capital * risk_pct / 100
        shares = int(risk_cash // ((entry - stop) * 100)) * 100
        st.metric("依風險預算估算股數", f"{shares:,} 股")
        st.caption(f"估算風險預算約 NT${risk_cash:,.0f}；未納入手續費、證交稅、滑價、跳空與流動性風險。此數值不是買進建議。")
    else:
        st.warning("請輸入大於 0 且低於進場價的停損價。")

st.divider()
st.caption(f"頁面產生時間：{datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}（台灣時間）")
st.caption("本工具僅供資訊整理與教育研究，不構成個人化投資建議。資料來源可能延遲、錯誤或中斷；請自行查證並承擔交易決策責任。")
