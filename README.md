# TechStock AI｜台股科技新聞與短線研究助理（第一版）

這是一個可部署到網路的 Streamlit 網站，並可透過 GitHub Actions 每個交易日產生研究報告及寄送電子郵件。

## 本機執行
需要 Python 3.10 或更新版本。

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## 部署成公開網站
1. 建立 GitHub 帳號：https://github.com/signup
2. 建立新的 repository，將本專案檔案上傳（不要上傳密碼或金鑰）。
3. 前往 https://share.streamlit.io/，登入並選擇 Create app。
4. 選擇 repository、branch，主程式指定 `app.py`，再按 Deploy。
5. 部署成功後會得到 `*.streamlit.app` 網址。

官方文件：
- Streamlit 部署：https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app
- GitHub Actions 排程：https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows

## 設定每日電子郵件
在 GitHub repository 的 Settings → Secrets and variables → Actions，新增以下 Repository secrets：
- `SMTP_HOST`：Gmail 通常為 `smtp.gmail.com`
- `SMTP_PORT`：`587`
- `SMTP_USER`：寄件 Gmail 地址
- `SMTP_PASSWORD`：Gmail 應用程式密碼（需先啟用兩步驟驗證並建立 App Password）
- `REPORT_FROM`：寄件地址
- `REPORT_TO`：收件地址

不要把郵件密碼放進程式碼或公開 repository。完成後，到 Actions → Taiwan TechStock Daily Report → Run workflow 手動測試。排程預設為週一至週五台灣時間約 07:10，GitHub 排程可能延遲。

## 資料來源與限制
- 科技新聞：Google News RSS 搜尋結果；請點進原文核實來源與發布時間。
- 歷史行情：透過 `yfinance` 讀取 Yahoo Finance 歷史資料。此為非官方介面，可能延遲、缺漏或中斷；不可視為交易所即時報價。
- 本版技術分數依收盤價相對 MA5、MA5 相對 MA20，以及成交量相對近 20 日均量計算。分數不是買賣指令，策略尚未經歷史回測驗證。
- 本版尚未串接券商下單，也不保證投資報酬。請納入交易成本、滑價、跳空、流動性與漲跌幅限制，並自行查證資料。
- 網站部署、資料來源與郵件供應商的免費方案和條款可能變動，請以服務商當前規定為準。
