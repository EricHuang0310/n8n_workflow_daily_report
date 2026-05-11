"""
node_09_confirm_question.py - 9.與客戶確認問題
================================================
報表項目 (項次 5):
  1. 進入此節點之數量
  2. 客戶停留時間
  3. 客戶正向回覆的筆數
  4. 客戶負向回覆的筆數
  5. 重聽的筆數 (other)
  6. 直接表明要轉接專員的筆數 (新增, Text Classifier 判斷)

對應 n8n 節點 (v0.0.1):
  set_confirm_response → return_confirm → receive_confirmation → save_confirm
  → Text Classifier (yes/no/error)
      yes → save_human1 → 轉接專員流程
      no  → set_confirm → ambiguous_intent_analyze → ambiguity_router
            (positive / negative / other)

判斷邏輯 (依優先順序):
  - Text Classifier 判定 "yes" → response_type = "transfer_human"
  - ambiguity_router selected_intent == "negative" → "negative"
  - ambiguity_router selected_intent == "other"    → "other"
  - 其他 (含 "positive" 或具體意圖名稱)             → "positive"
"""

from utils import (
    get_run_data,
    get_node_output,
    get_node_execution_time,
    node_was_executed,
    calc_node_duration_seconds,
)


def _get_text_classifier_label(run_data: dict) -> str | None:
    """
    Text Classifier 是 LangChain textClassifier，輸出分支由 entry 的
    main 索引判斷 (0=yes, 1=no, 2=error/fallback)。
    透過後續節點是否觸發來推斷類別。
    """
    if not node_was_executed(run_data, "Text Classifier"):
        return None
    # 觀察後續節點
    if node_was_executed(run_data, "save_human1"):
        return "yes"     # 客戶想轉接專員
    if node_was_executed(run_data, "set_confirm"):
        return "no"      # 進入下一步意圖比對
    if node_was_executed(run_data, "error_msg"):
        return "error"
    return "unknown"


def _determine_response_type(run_data: dict) -> str | None:
    """
    判斷客戶在「確認問題」階段的回覆類型。
    回傳: 'transfer_human' / 'positive' / 'negative' / 'other' / None
    """
    # 1) Text Classifier 先判定是否為「直接要求轉接專員」
    if _get_text_classifier_label(run_data) == "yes":
        return "transfer_human"

    # 2) 再看 ambiguous_intent_analyze
    analyze_output = get_node_output(run_data, "ambiguous_intent_analyze")
    if not analyze_output:
        return None

    output_obj = analyze_output.get("output", {})
    selected = output_obj.get("selected_intent", "")

    if selected == "negative":
        return "negative"
    if selected == "other":
        return "other"
    # "positive" 或具體意圖名稱皆視為正向確認
    if selected:
        return "positive"
    return None


def extract(execution: dict) -> dict | None:
    """
    從單一 execution 提取「9.與客戶確認問題」節點數據。
    """
    run_data = get_run_data(execution)

    # 核心節點: set_confirm_response (播放確認語音)
    if not node_was_executed(run_data, "set_confirm_response"):
        return None

    # 客戶停留時間: 從 return_confirm (開始播音) 到 receive_confirmation (收到回覆)
    stay_duration_sec = calc_node_duration_seconds(
        run_data, "return_confirm", "receive_confirmation"
    )

    # 客戶回覆文字: set_confirm 節點的 confirm_query (Text Classifier "no" 路徑)
    confirm_output = get_node_output(run_data, "set_confirm")
    confirm_text = confirm_output.get("confirm_query") if confirm_output else None
    if not confirm_text:
        recv = get_node_output(run_data, "receive_confirmation")
        if recv:
            confirm_text = recv.get("body", {}).get("text")

    response_type = _determine_response_type(run_data)
    text_classifier_label = _get_text_classifier_label(run_data)

    # 取得 session 資訊
    extract_output = get_node_output(run_data, "extract_intent")
    session_id = extract_output.get("sessionID") if extract_output else None
    if not session_id:
        webhook = get_node_output(run_data, "receive_message_API")
        body = webhook.get("body", {}) if webhook else {}
        session_id = body.get("sessionID")

    return {
        "node": "9.與客戶確認問題",
        "entered": True,
        "session_id": session_id,
        "customer_confirm_text": confirm_text,
        "response_type": response_type,
        "text_classifier_label": text_classifier_label,
        "stay_duration_sec": stay_duration_sec,
        "llm_analysis_time_ms": get_node_execution_time(run_data, "ambiguous_intent_analyze"),
    }


def aggregate(records: list[dict]) -> dict:
    """彙總多筆 execution 的「9.與客戶確認問題」數據。"""
    valid = [r for r in records if r is not None]

    positive_count = sum(1 for r in valid if r.get("response_type") == "positive")
    negative_count = sum(1 for r in valid if r.get("response_type") == "negative")
    other_count = sum(1 for r in valid if r.get("response_type") == "other")
    transfer_count = sum(1 for r in valid if r.get("response_type") == "transfer_human")

    total_stay = 0.0
    stay_n = 0
    for r in valid:
        if r.get("stay_duration_sec") is not None:
            total_stay += r["stay_duration_sec"]
            stay_n += 1

    return {
        "report_item": "9.與客戶確認問題",
        "total_count": len(valid),
        "positive_count": positive_count,
        "negative_count": negative_count,
        "other_replay_count": other_count,
        "direct_transfer_human_count": transfer_count,
        "avg_stay_duration_sec": round(total_stay / stay_n, 3) if stay_n else None,
    }
