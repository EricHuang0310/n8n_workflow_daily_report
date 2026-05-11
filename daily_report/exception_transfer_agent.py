"""
exception_transfer_agent.py - 例外1: 客戶直接說明轉專員
=========================================================
報表項目 (例外情境 項次 1):
  1. 第一次說明轉專員的筆數    (count == 1)
  2. 第二次說明轉專員並轉接的筆數 (count >= 2)
  3. 客戶ID

對應 n8n 節點 (v0.0.1):
  共有三條偵測「客戶說要轉接專員」的路徑:

  路徑 A (首次提問即說轉專員):
    extract_intent → if_to_human → save_human → get_human → if_count_human
      - count == 1 (返回 set_confirm_response 確認, 不直接轉接)
      - count >= 2 (response_to_human → retrun_to_human → to_human_response1)

  路徑 B (Confirm 階段 Text Classifier 判定 "yes"):
    save_confirm → Text Classifier
      → save_human1 → get_human1 → if_count_human1
          - count == 1 (返回 set_confirm 給意圖分析)
          - count >= 2 (response_to_human)

  路徑 C (Other → 再次提問又說轉專員):
    receive_confirmation_again → intent_identification2 → extract_intent2
      → save_other → if_to_human2 → save_human2 → get_human2 → if_count_human2
          - count == 1 (返回 get_otehr)
          - count >= 2 (response_to_human1)

  路徑 D (是否有其他問題 階段, 客戶要求轉專員):
    other_question_classifier → response_to_human1
"""

from utils import (
    get_run_data,
    get_node_output,
    node_was_executed,
)


def _human_count(run_data: dict, get_node: str) -> int | None:
    out = get_node_output(run_data, get_node)
    return out.get("messagesCount") if out else None


def extract(execution: dict) -> dict | None:
    """
    從單一 execution 提取「例外1: 客戶直接說明轉專員」數據。
    """
    run_data = get_run_data(execution)

    # 路徑 A: 首次提問即說轉專員
    path_a = node_was_executed(run_data, "save_human")
    a_count = _human_count(run_data, "get_human")
    a_transferred = node_was_executed(run_data, "response_to_human")

    # 路徑 B: Confirm 階段 Text Classifier yes
    path_b = node_was_executed(run_data, "save_human1")
    b_count = _human_count(run_data, "get_human1")
    # 路徑 B 的轉接也走 response_to_human (來自 if_count_human1)
    # 因為 response_to_human 同時是路徑 A 與 B 的終點, 用 count 區分

    # 路徑 C: Other 後再次提問又說轉專員
    path_c = node_was_executed(run_data, "save_human2")
    c_count = _human_count(run_data, "get_human2")
    c_transferred = node_was_executed(run_data, "response_to_human1") and not node_was_executed(run_data, "other_question_classifier")

    # 路徑 D: 是否有其他問題階段
    path_d = (
        node_was_executed(run_data, "other_question_classifier")
        and node_was_executed(run_data, "response_to_human1")
    )

    # 顯式 ERROR 路徑也可能轉專員 (response_to_human2 / error_to_human)
    error_to_human = node_was_executed(run_data, "error_to_human")

    if not (path_a or path_b or path_c or path_d or error_to_human):
        return None

    # 是否最終轉接 (走到 response_to_human 系列或 error_to_human)
    final_transferred = (
        a_transferred
        or node_was_executed(run_data, "response_to_human1")
        or node_was_executed(run_data, "response_to_human2")
        or error_to_human
    )

    # 第一次說明 vs 第二次轉接 (任一路徑 count==1 視為第一次, count>=2 視為第二次)
    first_time = False
    second_time = False
    for cnt in (a_count, b_count, c_count):
        if cnt is None:
            continue
        if cnt == 1:
            first_time = True
        elif cnt >= 2:
            second_time = True

    # 取得客戶 ID
    webhook = get_node_output(run_data, "receive_message_API")
    body = webhook.get("body", {}) if webhook else {}
    customer_id = body.get("customerID")
    session_id = body.get("sessionID")

    # 偵測到的意圖
    intents = []
    extract_output = get_node_output(run_data, "extract_intent")
    if extract_output:
        intents = extract_output.get("intent", []) or []

    return {
        "exception": "客戶直接說明轉專員",
        "session_id": session_id,
        "customer_id": customer_id,
        "intents": intents,
        "path_a_first_intent": path_a,
        "path_b_text_classifier": path_b,
        "path_c_second_intent": path_c,
        "path_d_other_question": path_d,
        "error_to_human": error_to_human,
        "first_time_redirect": first_time and not second_time,
        "second_time_transferred": second_time or final_transferred and not first_time,
        "final_transferred": final_transferred,
    }


def aggregate(records: list[dict]) -> dict:
    """彙總多筆 execution 的「例外1: 客戶直接說明轉專員」數據。"""
    valid = [r for r in records if r is not None]

    first_time = sum(1 for r in valid if r.get("first_time_redirect"))
    second_time = sum(1 for r in valid if r.get("second_time_transferred"))
    transferred = sum(1 for r in valid if r.get("final_transferred"))
    customer_ids = sorted(set(
        r["customer_id"] for r in valid if r.get("customer_id")
    ))

    path_distribution = {
        "首次提問即說轉專員":     sum(1 for r in valid if r.get("path_a_first_intent")),
        "確認階段表達要轉接專員": sum(1 for r in valid if r.get("path_b_text_classifier")),
        "再次提問仍說轉專員":     sum(1 for r in valid if r.get("path_c_second_intent")),
        "其他問題階段要求轉專員": sum(1 for r in valid if r.get("path_d_other_question")),
        "錯誤路徑進入轉專員":     sum(1 for r in valid if r.get("error_to_human")),
    }

    return {
        "report_item": "例外1.客戶直接說明轉專員",
        "total_occurrences": len(valid),
        "first_time_redirect_count": first_time,
        "second_time_transfer_count": second_time,
        "final_transferred_count": transferred,
        "path_distribution": path_distribution,
        "customer_ids": customer_ids,
    }
