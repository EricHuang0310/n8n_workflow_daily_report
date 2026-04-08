"""
exception_error.py - 例外4: 任一節點發生系統 ERROR
=====================================================
報表項目 (例外情境 項次 4):
  1. 發生次數並轉接專員的筆數
  2. ERROR 代碼/類型
  3. ERROR 發生的節點

對應 n8n 節點:
  - 任何節點的 executionStatus != 'success'
  - intent_identification 的 onError: continueErrorOutput → error_to_human
  - 全域 execution.status == 'error' 或 'crashed'
"""

from utils import (
    get_run_data,
    get_node_output,
    get_node_status,
    node_was_executed,
    get_all_node_names,
)


def extract(execution: dict) -> dict | None:
    """
    從單一 execution 提取「例外4: 系統 ERROR」數據。
    掃描所有節點找出 error。
    """
    run_data = get_run_data(execution)
    exec_status = execution.get("status")

    error_nodes = []
    error_details = []

    # 掃描所有節點的執行狀態
    for node_name in get_all_node_names(run_data):
        status = get_node_status(run_data, node_name)
        if status and status != "success":
            entries = run_data.get(node_name, [])
            error_info = {
                "node": node_name,
                "status": status,
            }
            # 嘗試提取 error 訊息
            if entries:
                entry = entries[0]
                error_msg = entry.get("error", {})
                if isinstance(error_msg, dict):
                    error_info["error_message"] = error_msg.get("message", "")
                    error_info["error_type"] = error_msg.get("name", "")
                elif isinstance(error_msg, str):
                    error_info["error_message"] = error_msg
            error_nodes.append(node_name)
            error_details.append(error_info)

    # 檢查是否走了 error_to_human 路徑 (即使節點本身標記 success，
    # 因為 intent_identification 設定了 onError: continueErrorOutput)
    went_error_to_human = node_was_executed(run_data, "error_to_human")
    if went_error_to_human and "error_to_human" not in error_nodes:
        error_nodes.append("intent_identification (error output)")
        error_details.append({
            "node": "intent_identification",
            "status": "error_output_triggered",
            "error_message": "觸發 error output → 轉接真人客服",
        })

    # 全域 execution error
    is_execution_error = exec_status in ("error", "crashed")
    if is_execution_error and not error_nodes:
        error_nodes.append("execution_level")
        error_details.append({
            "node": "execution_level",
            "status": exec_status,
            "error_message": "整體 execution 失敗",
        })

    if not error_nodes and not is_execution_error and not went_error_to_human:
        return None

    # 取得客戶資訊
    webhook_output = get_node_output(run_data, "receive_message_API")
    body = webhook_output.get("body", {}) if webhook_output else {}

    return {
        "exception": "任一節點發生系統ERROR",
        "session_id": body.get("sessionID"),
        "customer_id": body.get("customerID"),
        "execution_status": exec_status,
        "error_nodes": error_nodes,
        "error_details": error_details,
        "transferred_to_human": went_error_to_human,
    }


def aggregate(records: list[dict]) -> dict:
    """彙總多筆 execution 的「例外4: 系統 ERROR」數據。"""
    valid = [r for r in records if r is not None]

    transferred_count = sum(1 for r in valid if r.get("transferred_to_human"))

    # 統計各節點的 error 發生次數
    error_node_dist = {}
    error_type_dist = {}
    for r in valid:
        for detail in r.get("error_details", []):
            node = detail.get("node", "unknown")
            error_node_dist[node] = error_node_dist.get(node, 0) + 1
            etype = detail.get("error_type") or detail.get("status", "unknown")
            error_type_dist[etype] = error_type_dist.get(etype, 0) + 1

    return {
        "report_item": "例外4.任一節點發生系統ERROR",
        "total_error_count": len(valid),
        "transferred_to_human_count": transferred_count,
        "error_node_distribution": error_node_dist,
        "error_type_distribution": error_type_dist,
    }
