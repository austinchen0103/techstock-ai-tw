from datetime import datetime
from zoneinfo import ZoneInfo
from email.message import EmailMessage
from urllib.parse import quote
import os
import smtplib
import feedparser
from analysis_core import analyze, TW, US, macro_data, macro_interpretation

TZ=ZoneInfo('Asia/Taipei')

def build_report():
    now=datetime.now(TZ).strftime('%Y-%m-%d %H:%M')
    lines=['# TechStock AI 台美股與通膨每日研究報告',f'產生時間：{now}（台灣時間）','','僅供研究參考，非投資建議。','', '## 科技新聞']
    url='https://news.google.com/rss/search?q='+quote('台灣 半導體 AI 科技')+'&hl=zh-TW&gl=TW&ceid=TW:zh-Hant'
    entries=feedparser.parse(url).entries
    for e in entries[:12]:lines.append(f"- {e.get('title','')}：{e.get('link','')}")
    if not entries:lines.append('- 暫無新聞資料')
    lines.extend(['','## 技術觀察'])
    for ticker,name in {**TW,**US}.items():
        r=analyze(ticker,name,'3mo')
        if r.get('狀態')=='正常':lines.append(f"- {name} ({ticker})：{r['分類']}；收盤 {r['收盤價']}；漲跌 {r['單日變動%']}%；MA5 {r['MA5']}；MA20 {r['MA20']}；量比 {r['量比']}；資料日期 {r['資料日期']}")
        else:lines.append(f"- {name} ({ticker})：{r['狀態']}")
    lines.extend(['','## 美國通膨與利率觀察'])
    macro=macro_data()
    for r in macro:
        lines.append(f"- {r['指標']}：{r['數值']} {r['單位']}；觀測期間 {r['觀測期間']}；{r['狀態']}")
    lines.extend(['']+['- '+note for note in macro_interpretation(macro)])
    return '\n'.join(lines)+'\n'

def send_email(body):
    keys=['SMTP_HOST','SMTP_USER','SMTP_PASSWORD','REPORT_TO']
    if not all(os.getenv(k) for k in keys):
        print('Email secrets missing; report saved only.')
        return
    msg=EmailMessage()
    msg['Subject']='台股科技每日研究報告｜'+datetime.now(TZ).strftime('%Y-%m-%d')
    msg['From']=os.getenv('REPORT_FROM',os.environ['SMTP_USER'])
    msg['To']=os.environ['REPORT_TO']
    msg.set_content(body)
    with smtplib.SMTP(os.environ['SMTP_HOST'],int(os.getenv('SMTP_PORT','587')),timeout=30) as server:
        server.starttls();server.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD']);server.send_message(msg)

if __name__=='__main__':
    report=build_report()
    with open('daily_report_'+datetime.now(TZ).strftime('%Y%m%d')+'.md','w',encoding='utf-8') as f:f.write(report)
    print(report)
    send_email(report)
