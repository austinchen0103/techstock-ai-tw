import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote

import feedparser
import pandas as pd
import yfinance as yf

TZ = ZoneInfo("Asia/Taipei")
WATCHLIST = [
    ("2330.TW", "台積電"), ("2454.TW", "聯發科"), ("2317.TW", "鴻海"),
    ("2382.TW", "廣達"), ("2308.TW", "台達電"), ("3711.TW", "日月光投控"),
]
FEEDS = [
    ("台灣科技", "https://news.google.com/rss/search?q=" + quote("台灣 科技 半導體 AI") + "&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
    ("台股電子", "https://news.google.com/rss/search?q=" + quote("台股 電子股 半導體 伺服器") + "&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
    ("AI 供應鏈", "https://news.google.com/rss/search?q=" + quote("AI 伺服器 GPU HBM 台灣供應鏈") + "&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
]

def collect_news(limit=12):
    out, seen = [], set()
    for category, url in FEEDS:
        try:
            parsed = feedparser.parse(url)
            for item in parsed.entries:
                title = getattr(item, "title", "").strip()
                link = getattr(item, "link", "")
                if not title or link in seen:
                    continue
                seen.add(link)
                out.append((category, title, getattr(item, "published", "時間未提供"), link))
        except Exception:
            pass
    return out[:limit]

def score_stock(ticker, name):
    try:
        hist = yf.Ticker(ticker).history(period="3mo")
        if hist.empty or len(hist) < 5:
            return {"代號": ticker, "名稱": name, "狀態": "無足夠資料"}
        close, volume = hist["Close"].dropna(), hist["Volume"].fillna(0)
        last, prev = float(close.iloc[-1]), float(close.iloc[-2])
        ma5 = float(close.tail(5).mean())
        ma20 = float(close.tail(20).mean()) if len(close) >= 20 else float(close.mean())
        avgvol = float(volume.tail(20).mean()) if len(volume) >= 20 else float(volume.mean())
        vr = float(volume.iloc[-1]) / avgvol if avgvol else 0
        pct = (last / prev - 1) * 100 if prev else 0
        score = (1 if last > ma5 else -1) + (1 if ma5 > ma20 else -1)
        if vr >= 1.5:
            score += 1 if pct > 0 else (-1 if pct < 0 else 0)
        label = "偏多觀察" if score >= 2 else ("偏空／觀望" if score <= -1 else "中性觀察")
        return {"代號": ticker, "名稱": name, "資料日期": str(hist.index[-1].date()),
                "收盤價": round(last, 2), "單日變動%": round(pct, 2),
                "MA5": round(ma5, 2), "MA20": round(ma20, 2),
                "量比": round(vr, 2), "研究分數": score, "分類": label, "狀態": "正常"}
    except Exception as e:
        return {"代號": ticker, "名稱": name, "狀態": f"讀取失敗：{type(e).__name__}"}

def build_report():
    now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    lines = [f"# TechStock AI 台股每日研究報告", f"產生時間：{now}（台灣時間）", "",
             "> 本報告為研究輔助，不構成買賣指令。行情可能延遲或缺漏，請確認資料日期。", "",
             "## 一、科技新聞"]
    news = collect_news()
    if news:
        for category, title, published, link in news:
            lines.append(f"- **{title}**（{category}；{published}）\n  原文：{link}")
    else:
        lines.append("- 今日 RSS 無法取得新聞，請稍後重試。")
    lines += ["", "## 二、自選股技術觀察"]
    rows = [score_stock(t, n) for t, n in WATCHLIST]
    for r in rows:
        if r.get("狀態") == "正常":
            lines.append(f"- **{r['代號']} {r['名稱']}｜{r['分類']}**：收盤 {r['收盤價']}；單日 {r['單日變動%']}%；MA5 {r['MA5']}；MA20 {r['MA20']}；量比 {r['量比']}；資料日期 {r['資料日期']}。")
        else:
            lines.append(f"- **{r['代號']} {r['名稱']}**：{r['狀態']}")
    lines += ["", "## 三、評分依據與限制",
              "- 技術分數依收盤價相對 MA5、MA5 相對 MA20，以及成交量相對近 20 日均量計算。",
              "- 「偏多觀察」僅代表上述簡單技術條件較正向，不代表預期報酬為正，也未納入完整基本面、法人籌碼、盤中資訊或市場突發事件。",
              "- 不要單憑新聞標題或分數追價；應確認原始來源、流動性、交易成本、停損條件與部位大小。",
              "", "## 四、資料來源", "- 科技新聞：Google News RSS 搜尋結果（請點入原文核實）。",
              "- 歷史行情：Yahoo Finance/yfinance 非官方介面；資料可能延遲、修正或不可用，依服務條款使用。",
              ""]
    return "\n".join(lines)

def send_email(subject, body):
    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    to_addr = os.getenv("REPORT_TO", "")
    from_addr = os.getenv("REPORT_FROM", user)
    if not all([host, user, password, to_addr, from_addr]):
        print("Email not configured; report printed to console only.")
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(body)
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
    print("Email sent.")
    return True

if __name__ == "__main__":
    report = build_report()
    print(report)
    filename = "daily_report_" + datetime.now(TZ).strftime("%Y%m%d") + ".md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)
    send_email("台股科技每日研究報告｜" + datetime.now(TZ).strftime("%Y-%m-%d"), report)
