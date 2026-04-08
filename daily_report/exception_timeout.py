"""
exception_timeout.py - 例外3: 任一流程 Time Out
====================================================
報表項目 (例外情境 項次 3):
  1. 第一次 Time Out 的筆數
  2. 連續兩次 Time Out 並轉接專員的筆數
  3. Time Out 發生的節點

對應 n8n 節點:
  - receive_confirmation (Wait 節點) 等待客戶回覆 timeout
  - receive_confirmation_again (Wait 節點) 第二次等待 timeout
  - 在 execution log 中，timeout 的表現為 execution.status == 'waiting' 或
    特定 wait 節點有 waitTill 時間戳
  
注意: n8n 的 Wait 節點 timeout 通常不在同一個 execution 內完成，
      而是 execution 狀態變成 'waiting'。需要根據 execution 的整體狀態來判斷。
"""

from utils import (
    get_run_data,
    get_node_output,
    get_node_execution_time,
    node_was_executed,
    get_all_node_names,
    get_node_status,
)


def extract(execution: dict) -> dict | None:
    """
    從單一 execution 提取「例外3: Time Out」數據。
    
    Time Out 判斷:
    1. execution.status == 'waiting' 且 waitTill 有值 → 等待中
    2. execution.status == 'success' 但最後執行節點是 wait 類 → 可能 timeout
    3. 特定節點 executionTime 超過閾值
    """
    run_data = get_run_data(execution)
    exec_status = execution.get("status")
    wait_till = execution.get("waitTill")
    last_node = (
        execution.get("data", {})
        .get("resultData", {})
        .get("lastNodeExecuted")
    )

    # 判斷是否為 timeout 情境
    is_timeout = False
    timeout_node = None

    # 情境 1: execution 狀態為 waiting (n8n 正在等客戶回覆)
    if exec_status == "waiting" and wait_till:
        is_timeout = True
        timeout_node = last_node

    # 情境 2: 檢查各節點的 HTTP timeout
    # intent_identification 設定了 5000ms timeout
    if node_was_executed(run_data, "intent_identification"):
        exec_time = get_node_execution_time(run_data, "intent_identification")
        status = get_node_status(run_data, "intent_identification")
        if status != "success" and exec_time and exec_time >= 5000:
            is_timeout = True
            timeout_node = "intent_identification"

    # 情境 3: 檢查 LLM 分析節點是否超時
    if node_was_executed(run_data, "ambiguous_intent_analyze"):
        exec_time = get_node_execution_time(run_data, "ambiguous_intent_analyze")
        status = get_node_status(run_data, "ambiguous_intent_analyze")
        if status != "success" and exec_time and exec_time >= 10000:
            is_timeout = True
            timeout_node = "ambiguous_intent_analyze"

    if not is_timeout:
        return None

    # 取得 session 資訊
    webhook_output = get_node_output(run_data, "receive_message_API")
    body = webhook_output.get("body", {}) if webhook_output else {}

    return {
        "exception": "任一流程TimeOut",
        "session_id": body.get("sessionID"),
        "customer_id": body.get("customerID"),
        "timeout_node": timeout_node,
        "execution_status": exec_status,
        "wait_till": wait_till,
        "last_node_executed": last_node,
    }


def aggregate(records: list[dict]) -> dict:
    """彙總多筆 execution 的「例外3: Time Out」數據。"""
    valid = [r for r in records if r is not None]

    # 各節點 timeout 統計
    timeout_node_dist = {}
    for r in valid:
        node = r.get("timeout_node", "unknown")
        timeout_node_dist[node] = timeout_node_dist.get(node, 0) + 1

    return {
        "report_item": "例外3.任一流程TimeOut",
        "total_timeout_count": len(valid),
        "timeout_node_distribution": timeout_node_dist,
    }
