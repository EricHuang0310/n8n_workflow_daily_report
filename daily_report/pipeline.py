"""
pipeline.py - 客服語音機器人 日報表產生器
==========================================
整合所有報表項目模組，從 n8n execution log 產出每日 Excel 報表。

使用方式:
  python pipeline.py <execution_log.json> [--output report_output.xlsx]

輸出格式: Excel (.xlsx)
  - Sheet 1 「總覽」: 報表 metadata + 各節點 / 例外情境的彙總指標
  - Sheet 2..N: 每個報表模組獨立一張明細 Sheet (一列一筆 execution)
"""

import sys
import os
from datetime import datetime, timezone

# 確保模組路徑正確
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import load_execution_log, get_execution_metadata
from excel_writer import build_excel_report

# ── 匯入各報表項目模組 ──────────────────────────────────
import node_07_customer_query
import node_08_intent_recognition
import node_09_confirm_question
import node_10_automation_check
import node_15_ivr_check
import node_18_sms_send
import node_19_other_questions
import exception_transfer_agent
import exception_misunderstanding
import exception_timeout
import exception_error


# ── 所有報表模組註冊表 ──────────────────────────────────
REPORT_MODULES = [
    {
        "id": "node_07",
        "name": "7.說出問題",
        "module": node_07_customer_query,
    },
    {
        "id": "node_08",
        "name": "8.理解問題",
        "module": node_08_intent_recognition,
    },
    {
        "id": "node_09",
        "name": "9.與客戶確認問題",
        "module": node_09_confirm_question,
    },
    {
        "id": "node_10",
        "name": "10.是否可自動化處理",
        "module": node_10_automation_check,
    },
    {
        "id": "node_15",
        "name": "15.是否為語音一站式",
        "module": node_15_ivr_check,
    },
    {
        "id": "node_18",
        "name": "18.說答案後發送訊息(SMS)",
        "module": node_18_sms_send,
    },
    {
        "id": "node_19",
        "name": "19.是否有其他問題",
        "module": node_19_other_questions,
    },
    {
        "id": "exception_01",
        "name": "例外1.客戶直接說明轉專員",
        "module": exception_transfer_agent,
    },
    {
        "id": "exception_02",
        "name": "例外2.機器人問題理解錯誤",
        "module": exception_misunderstanding,
    },
    {
        "id": "exception_03",
        "name": "例外3.任一流程TimeOut",
        "module": exception_timeout,
    },
    {
        "id": "exception_04",
        "name": "例外4.任一節點發生系統ERROR",
        "module": exception_error,
    },
]


def run_pipeline(log_filepath: str) -> dict:
    """
    主流程: 讀取 execution log → 逐一 execution 提取各項指標 → 彙總為日報表。
    """
    # 1. 載入 execution log
    executions = load_execution_log(log_filepath)
    print(f"[Pipeline] 載入 {len(executions)} 筆 execution records")

    # 2. 提取 execution metadata
    exec_meta_list = [get_execution_metadata(ex) for ex in executions]

    # 3. 對每個報表模組，逐一提取 & 彙總
    report_sections = {}
    detail_records = {}

    for mod_info in REPORT_MODULES:
        mod_id = mod_info["id"]
        mod_name = mod_info["name"]
        module = mod_info["module"]

        print(f"  → 處理 [{mod_name}] ...", end=" ")

        # 逐 execution 提取
        records = []
        for ex in executions:
            try:
                record = module.extract(ex)
                records.append(record)
            except Exception as e:
                print(f"\n    ⚠ Execution {ex.get('id')} 提取失敗: {e}")
                records.append(None)

        # 彙總
        try:
            summary = module.aggregate(records)
        except Exception as e:
            print(f"\n    ⚠ 彙總失敗: {e}")
            summary = {"error": str(e)}

        report_sections[mod_id] = summary
        # 保留每筆明細 (去除 None)
        detail_records[mod_id] = [r for r in records if r is not None]
        print(f"OK ({sum(1 for r in records if r is not None)}/{len(records)} 筆)")

    # 4. 組裝最終報表
    # 時間範圍
    started_times = [
        m["started_at"] for m in exec_meta_list if m.get("started_at")
    ]
    stopped_times = [
        m["stopped_at"] for m in exec_meta_list if m.get("stopped_at")
    ]

    report = {
        "report_title": "客服語音機器人_每日數據報表",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_range": {
            "earliest_execution": min(started_times) if started_times else None,
            "latest_execution": max(stopped_times) if stopped_times else None,
            "total_executions": len(executions),
            "success_count": sum(
                1 for m in exec_meta_list if m.get("status") == "success"
            ),
            "error_count": sum(
                1 for m in exec_meta_list
                if m.get("status") in ("error", "crashed")
            ),
            "waiting_count": sum(
                1 for m in exec_meta_list if m.get("status") == "waiting"
            ),
        },
        "summary": report_sections,
        "detail_records": detail_records,
    }

    return report


def main():
    # 預設參數
    log_file = "../n8n範例log.json"
    today_str = datetime.now().strftime("%Y%m%d")
    output_file = f"CustomerServiceLog_{today_str}.xlsx"

    # 解析命令列參數
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--output" and i + 1 < len(args):
            output_file = args[i + 1]
            i += 2
        elif not args[i].startswith("-"):
            log_file = args[i]
            i += 1
        else:
            i += 1

    if not log_file:
        print("使用方式: python pipeline.py <execution_log.json> [--output report.xlsx]")
        print()
        print("範例:")
        print("  python pipeline.py n8n範例log.json")
        print("  python pipeline.py n8n範例log.json --output 2026-04-02_report.xlsx")
        sys.exit(1)

    if not os.path.exists(log_file):
        print(f"錯誤: 找不到檔案 {log_file}")
        sys.exit(1)

    print("=" * 60)
    print("  客服語音機器人 - 每日數據報表產生器")
    print("=" * 60)
    print(f"[Pipeline] 輸入檔案: {log_file}")
    print(f"[Pipeline] 輸出檔案: {output_file}")
    print()

    report = run_pipeline(log_file)
    build_excel_report(report, output_file)
    print(f"\n[Pipeline] Excel 報表已儲存至: {output_file}")

    # 印出摘要
    print()
    print("=" * 60)
    print("  報表摘要")
    print("=" * 60)
    summary = report["summary"]
    for mod_info in REPORT_MODULES:
        mod_id = mod_info["id"]
        mod_name = mod_info["name"]
        section = summary.get(mod_id, {})
        count = section.get("total_count", section.get("total_occurrences",
                section.get("total_error_count", section.get("total_timeout_count", 0))))
        print(f"  {mod_name:　<20} → {count} 筆")

    print()
    print(f"  總 execution 數: {report['data_range']['total_executions']}")
    print(f"  成功: {report['data_range']['success_count']}")
    print(f"  錯誤: {report['data_range']['error_count']}")
    print(f"  等待中: {report['data_range']['waiting_count']}")
    print("=" * 60)


if __name__ == "__main__":
    main()