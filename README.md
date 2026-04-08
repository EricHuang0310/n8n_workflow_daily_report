# 客服語音機器人 - 每日數據報表產生器

## 專案概述

本專案從 n8n 客服語音機器人的 **Execution Log** 中提取數據，產出每日 Excel 報表。
每個報表項目獨立一個 Python 檔案，最後由 `pipeline.py` 整合，透過 `excel_writer.py` 輸出為 `.xlsx`。

## 檔案結構

```
daily_report/
├── pipeline.py                      # 主流程 - 整合所有模組，產出 Excel 報表
├── excel_writer.py                  # Excel 輸出 - 總覽 + 每節點明細 Sheet
├── utils.py                         # 共用工具 - 解析 execution log
├── requirements.txt                 # 依賴套件 (openpyxl)
├── node_07_customer_query.py        # 7.說出問題
├── node_08_intent_recognition.py    # 8.理解問題
├── node_09_confirm_question.py      # 9.與客戶確認問題
├── node_10_automation_check.py      # 10.是否可自動化處理
├── node_15_ivr_check.py             # 15.是否為語音一站式
├── node_18_sms_send.py              # 18.說答案後發送訊息(SMS)
├── node_19_other_questions.py       # 19.是否有其他問題
├── exception_transfer_agent.py      # 例外1.客戶直接說明轉專員
├── exception_misunderstanding.py    # 例外2.機器人問題理解錯誤
├── exception_timeout.py             # 例外3.任一流程 Time Out
├── exception_error.py               # 例外4.任一節點發生系統 ERROR
└── README.md                        # 本文件
```

## 使用方式

```bash
# 首次執行前: 安裝依賴
pip install -r daily_report/requirements.txt

# 基本使用 (預設輸出 CustomerServiceLog_YYYYMMDD.xlsx)
cd daily_report
python pipeline.py ../n8n範例log.json

# 指定輸出路徑
python pipeline.py ../n8n範例log.json --output 2026-04-02_report.xlsx
```

## 報表項目與 n8n 節點對應表

| 報表項目 | Python 模組 | 關鍵 n8n 節點 |
|---------|------------|--------------|
| 7.說出問題 | `node_07_customer_query` | `receive_message_API` |
| 8.理解問題 | `node_08_intent_recognition` | `intent_identification`, `extract_intent` |
| 9.與客戶確認問題 | `node_09_confirm_question` | `ambiguous_intent_analyze`, `ambiguity_router` |
| 10.是否可自動化處理 | `node_10_automation_check` | `automation_router`, `*_response` 節點 |
| 15.是否為語音一站式 | `node_15_ivr_check` | `IVR_response`, `SMS_response` |
| 18.說答案後發送訊息(SMS) | `node_18_sms_send` | `SMS_response` (⚠ workflow 部分節點尚未實作) |
| 19.是否有其他問題 | `node_19_other_questions` | ⚠ workflow 尚未實作 |
| 例外1.轉專員 | `exception_transfer_agent` | `negative_response_to_human` |
| 例外2.理解錯誤 | `exception_misunderstanding` | `save_negative_count`, `save_other_count` |
| 例外3.Time Out | `exception_timeout` | Wait 節點, HTTP timeout |
| 例外4.系統ERROR | `exception_error` | `error_to_human`, 任一失敗節點 |

## 輸出格式

輸出為 **Excel (.xlsx)**，共 12 個 Sheet：

| Sheet | 內容 |
|-------|------|
| `總覽` | 報表 metadata + 每個模組的彙總指標 (key-value + 分布子表) |
| `07_說出問題` ~ `19_是否有其他問題` | 每節點一張明細 Sheet，一列一筆 execution |
| `例外01_轉專員` ~ `例外04_系統ERROR` | 每種例外情境一張明細 Sheet |

- **總覽 Sheet** 集中呈現 PDF `報表需求項目` 要求的所有彙總指標 (進入此節點之數量、客戶停留時間、各種筆數分布等)，方便快速稽核。
- **每個節點 Sheet** 是純明細表格，欄位為該模組 `extract()` 回傳的所有 key 聯集，`session_id` / `customer_id` 等固定欄位置於前方。
- **`18_說答案後發送訊息SMS` / `19_是否有其他問題`** 因 workflow 尚未完整實作，Sheet 頂端會標註 `⚠ workflow 尚未完整實作`，等 workflow 擴充後即可自動補齊指標。

## 各模組 extract / aggregate 設計模式

每個模組遵循相同介面：

```python
def extract(execution: dict) -> dict | None:
    """從單一 execution 提取該報表項目的數據。無資料回傳 None。"""

def aggregate(records: list[dict]) -> dict:
    """彙總多筆 extract 結果為報表摘要。"""
```

## 擴展方式

1. 新增報表項目 → 建立新的 `.py` 檔，實作 `extract()` 和 `aggregate()`
2. 在 `pipeline.py` 的 `REPORT_MODULES` 列表中註冊
3. 完成

## 資料來源

- **Execution Log**: 透過 n8n API `GET /executions` 取得
- **Workflow 定義**: `客服語音機器人_NEW.json`
- **報表需求**: `報表需求項目.pdf` (CSR-VBOT-006)
