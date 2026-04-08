# 客服語音機器人 - 每日數據報表產生器

## 專案概述

本專案從 n8n 客服語音機器人的 **Execution Log** 中提取數據，產出每日報表。
每個報表項目獨立一個 Python 檔案，最後由 `pipeline.py` 整合並輸出 JSON 報表。

## 檔案結構

```
n8n_report/
├── pipeline.py                      # 主流程 - 整合所有模組，產出報表
├── utils.py                         # 共用工具 - 解析 execution log
├── node_07_customer_query.py        # 7.說出問題
├── node_08_intent_recognition.py    # 8.理解問題
├── node_09_confirm_question.py      # 9.與客戶確認問題
├── node_10_automation_check.py      # 10.是否可自動化處理
├── node_15_ivr_check.py             # 15.是否為語音一站式
├── exception_transfer_agent.py      # 例外1.客戶直接說明轉專員
├── exception_misunderstanding.py    # 例外2.機器人問題理解錯誤
├── exception_timeout.py             # 例外3.任一流程 Time Out
├── exception_error.py               # 例外4.任一節點發生系統 ERROR
└── README.md                        # 本文件
```

## 使用方式

```bash
# 基本使用
python pipeline.py <execution_log.json>

# 指定輸出路徑
python pipeline.py n8n範例log.json --output 2026-04-02_report.json
```

## 報表項目與 n8n 節點對應表

| 報表項目 | Python 模組 | 關鍵 n8n 節點 |
|---------|------------|--------------|
| 7.說出問題 | `node_07_customer_query` | `receive_message_API` |
| 8.理解問題 | `node_08_intent_recognition` | `intent_identification`, `extract_intent` |
| 9.與客戶確認問題 | `node_09_confirm_question` | `ambiguous_intent_analyze`, `ambiguity_router` |
| 10.是否可自動化處理 | `node_10_automation_check` | `automation_router`, `*_response` 節點 |
| 15.是否為語音一站式 | `node_15_ivr_check` | `IVR_response`, `SMS_response` |
| 例外1.轉專員 | `exception_transfer_agent` | `negative_response_to_human` |
| 例外2.理解錯誤 | `exception_misunderstanding` | `save_negative_count`, `save_other_count` |
| 例外3.Time Out | `exception_timeout` | Wait 節點, HTTP timeout |
| 例外4.系統ERROR | `exception_error` | `error_to_human`, 任一失敗節點 |

## 輸出格式

選用 **JSON** 而非 CSV，原因：
- 報表含巢狀結構（意圖分布、錯誤詳情、客戶查詢列表）
- 各報表項目的欄位維度不同，CSV 無法自然表達
- JSON 易於對接前端 Dashboard / BI 工具

### 輸出結構

```json
{
  "report_title": "客服語音機器人_每日數據報表",
  "generated_at": "2026-04-02T08:00:00+00:00",
  "data_range": {
    "earliest_execution": "...",
    "latest_execution": "...",
    "total_executions": 100,
    "success_count": 95,
    "error_count": 3,
    "waiting_count": 2
  },
  "summary": {
    "node_07": { "total_count": 100, "avg_stay_duration_sec": 1.5, ... },
    "node_08": { "total_count": 100, "clear_question_count": 80, ... },
    "node_09": { "positive_count": 70, "negative_count": 20, ... },
    ...
  },
  "detail_records": {
    "node_07": [ { 每筆 execution 的明細 }, ... ],
    ...
  }
}
```

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
