"""
exception_timeout.py - 例外3: 任一流程 Time Out
====================================================
報表項目 (例外情境 項次 3):
  1. 第一次 Time Out 的筆數
  2. 連續兩次 Time Out 並轉接專員的筆數
  3. Time Out 發生的節點

對應 n8n 行為:
  - Wait 節點 (resume=webhook) 等待客戶回覆。若客戶未在期限內回覆，
    n8n execution 會被 cancel / timeout，最後一個 wait 節點的
    executionStatus 仍為 "waiting"。
  - 在 execution log 中表現為:
      execution.status in ("canceled", "waiting", "stopped")
      AND 最後執行的節點是 Wait 類節點且 status == "waiting"
  - intent_identification HTTP 節點設定了 5000ms timeout，
    若 LLM 服務超時，會走 onError → error_msg/error_to_human (例外4 處理)。

v0.0.1 中已知 Wait 節點:
  receive_confirmation, receive_confirmation_again, receive_confirmation_message,
  receive_other_question, receive_check_phone, receive_speck_phone, receive_confirm_phone
"""

from utils import (
    get_run_data,
    get_node_output,
    get_node_execution_time,
    get_node_status,
    node_was_executed,
)


# Wait 節點 (resume=webhook) 列表
WAIT_NODES = [
    "receive_confirmation",
    "receive_confirmation_again",
    "receive_confirmation_message",
    "receive_other_question",
    "receive_check_phone",
    "receive_speck_phone",
    "receive_confirm_phone",
]

# 執行狀態被視為 timeout / 客戶未回覆的情境
TIMEOUT_EXEC_STATUS = {"canceled", "waiting", "stopped", "crashed"}


def _find_pending_wait_node(run_data: dict) -> str | None:
    """找出仍停留在 'waiting' 狀態的 Wait 節點 (代表 timeout)。"""
    for node in WAIT_NODES:
        if not node_was_executed(run_data, node):
            continue
        status = get_node_status(run_data, node)
        if status == "waiting":
            return node
    return None


def extract(execution: dict) -> dict | None:
    """
    從單一 execution 提取「例外3: Time Out」數據。
    """
    run_data = get_run_data(execution)
    exec_status = execution.get("status")
    last_node = (
        execution.get("data", {})
        .get("resultData", {})
        .get("lastNodeExecuted")
    )

    is_timeout = False
    timeout_node = None

    # 情境 1: Wait 節點仍 waiting → 客戶未回覆 → timeout
    pending_wait = _find_pending_wait_node(run_data)
    if pending_wait:
        is_timeout = True
        timeout_node = pending_wait

    # 情境 2: execution 狀態為 canceled / waiting / stopped，
    #         且 lastNodeExecuted 是 Wait 節點
    elif exec_status in TIMEOUT_EXEC_STATUS and last_node in WAIT_NODES:
        is_timeout = True
        timeout_node = last_node

    # 情境 3: intent_identification HTTP timeout (5000ms)
    if node_was_executed(run_data, "intent_identification"):
        exec_time = get_node_execution_time(run_data, "intent_identification")
        status = get_node_status(run_data, "intent_identification")
        if status != "success" and exec_time and exec_time >= 5000:
            is_timeout = True
            timeout_node = timeout_node or "intent_identification"

    if not is_timeout:
        return None

    # 客戶資訊
    webhook = get_node_output(run_data, "receive_message_API")
    body = webhook.get("body", {}) if webhook else {}

    return {
        "exception": "任一流程TimeOut",
        "session_id": body.get("sessionID"),
        "customer_id": body.get("customerID"),
        "timeout_node": timeout_node,
        "execution_status": exec_status,
        "last_node_executed": last_node,
    }


def aggregate(records: list[dict]) -> dict:
    """彙總多筆 execution 的「例外3: Time Out」數據。"""
    valid = [r for r in records if r is not None]

    timeout_node_dist = {}
    for r in valid:
        node = r.get("timeout_node", "unknown")
        timeout_node_dist[node] = timeout_node_dist.get(node, 0) + 1

    customer_ids = sorted(set(
        r["customer_id"] for r in valid if r.get("customer_id")
    ))

    return {
        "report_item": "例外3.任一流程TimeOut",
        "total_timeout_count": len(valid),
        "timeout_node_distribution": timeout_node_dist,
        "customer_ids": customer_ids,
    }
