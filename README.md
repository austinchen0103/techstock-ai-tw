# TechStock AI V3｜台美股、通膨與 AI 投資研究助理

保留 V2 台美股、Google News RSS、FRED 通膨與風險檢查功能，新增按鈕觸發的 OpenAI API 研究報告（未來 1、2、3 個月情境）。**不是交易系統，不保證預測準確。**

## Streamlit Cloud 部署

1. 上傳 `app.py`、`analysis_core.py`、`ai_research.py`、`requirements.txt`、`daily_report.py`、`README.md` 至 GitHub repository 根目錄。`.github/workflows/daily.yml` 為可選的自動報告排程。
2. 原有 Streamlit Cloud app 連接 main 分支的 `app.py`，GitHub 更新後通常會自動重新部署。
3. 在 Streamlit Cloud → app → Settings → Secrets，填入：

```toml
OPENAI_API_KEY = "sk-填入你自己的金鑰"
OPENAI_MODEL = "gpt-4.1-mini"
```

**金鑰只填在 Streamlit Secrets，絕不可貼進 GitHub、聊天室或 README。** OpenAI API 需要另外設定計費與額度，ChatGPT 訂閱不等於 API 額度。建議先設定 API 使用預算及限制公開網站存取權限。若不想公開服務，可使用 Streamlit 的存取控制設定。

## 分析限制

- 使用 yfinance 的一年歷史調整後收盤價與技術指標，可能延遲或缺漏；不是即時交易所報價。
- 新聞只讀 Google News RSS 的標題、時間、連結，**沒有讀新聞全文**，請點入來源核實。
- FRED 的觀測期間不等於公布日期，也未取得市場預期值。
- AI 提供條件式情境，不是統計驗證的未來報酬機率；本版尚未提供嚴謹的樣本外回測。
- 每次按下 AI 分析會呼叫付費 API；未設定 Secrets 時其他 V2 功能仍可使用。
