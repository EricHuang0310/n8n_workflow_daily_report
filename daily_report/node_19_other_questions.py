"""
node_19_other_questions.py - 19.是否有其他問題
=================================================
報表項目 (項次 14):
  1. 進入此節點之數量
  2. 客戶停留時間
  3. 客戶沒有其他問題的筆數
  4. 客戶有其他信用卡問題的筆數
  5. 客戶有銀行問題的筆數

對應 n8n 節點:
  目前 workflow 在 return_SMS / return_IVR / return_live_support 後，
  流程即結束 (save_IVR / save_live_support 是存歷史對話)，
  沒有「是否有其他問題」的後續 wait 節點。

  ⚠ 目前 workflow 狀態:
     此節點 **尚未在 workflow 中實作**。
     本模組預先建立好 extract/aggregate 框架，
     當 workflow 新增以下節點時，只需填入正確節點名稱即可啟用:
     
     預期 workflow 新增節點:
       - ask_other_question:        播放「請問還有什麼地方可以為您服務的?」
       - receive_other_question:     Wait 節點等待客戶回覆
       - other_question_router:      Switch 判斷 (沒有/信用卡問題/銀行問題)
       
     修改下方常數即可。
"""

from utils import (
    get_run_data,
    get_node_output,
    get_node_execution_time,
    node_was_executed,
    calc_node_duration_seconds,
)

# ── 節點名稱常數 (workflow 擴充後更新) ──────────
# 當 workflow 新增「是否有其他問題」功能時，填入對應節點名稱
NODE_ASK_OTHER = None            # 播放「還有什麼問題」的節點
NODE_RECEIVE_OTHER = None        # 等待客戶回覆的 wait 節點
NODE_OTHER_ROUTER = None         # 判斷客戶回覆的 switch 節點

# 如果 router 的輸出分支有特定節點名稱，也可以填入
NODE_NO_OTHER_QUESTION = None    # 客戶沒有其他問題 → 滿意度調查
NODE_HAS_CARD_QUESTION = None    # 客戶有信用卡問題 → 返回提問
NODE_HAS_BANK_QUESTION = None    # 客戶有銀行問題 → 返回主選單


def extract(execution: dict) -> dict | None:
    """
    從單一 execution 提取「19.是否有其他問題」數據。
    
    目前因 workflow 未實作此節點，會嘗試偵測:
    1. 若 NODE_ASK_OTHER 已設定 → 標準提取
    2. 若未設定 → 返回 None (不計入報表)
    """
    run_data = get_run_data(execution)

    # ── 方案 1: workflow 已實作，直接提取 ──
    if NODE_ASK_OTHER and node_was_executed(run_data, NODE_ASK_OTHER):
        # 取得 session 資訊
        webhook_output = get_node_output(run_data, "receive_message_API")
        body = webhook_output.get("body", {}) if webhook_output else {}

        record = {
            "node": "19.是否有其他問題",
            "entered": True,
            "session_id": body.get("sessionID"),
            "customer_id": body.get("customerID"),
        }

        # 客戶停留時間
        if NODE_RECEIVE_OTHER and node_was_executed(run_data, NODE_RECEIVE_OTHER):
            record["stay_duration_sec"] = calc_node_duration_seconds(
                run_data, NODE_ASK_OTHER, NODE_RECEIVE_OTHER
            )

        # 客戶回覆分類
        if NODE_NO_OTHER_QUESTION and node_was_executed(run_data, NODE_NO_OTHER_QUESTION):
            record["response_type"] = "no_other_question"
        elif NODE_HAS_CARD_QUESTION and node_was_executed(run_data, NODE_HAS_CARD_QUESTION):
            record["response_type"] = "has_card_question"
        elif NODE_HAS_BANK_QUESTION and node_was_executed(run_data, NODE_HAS_BANK_QUESTION):
            record["response_type"] = "has_bank_question"
        else:
            # 嘗試從 router 輸出判斷
            if NODE_OTHER_ROUTER and node_was_executed(run_data, NODE_OTHER_ROUTER):
                router_output = get_node_output(run_data, NODE_OTHER_ROUTER)
                record["response_type"] = "unknown"
                record["router_output"] = router_output
            else:
                record["response_type"] = "unknown"

        return record

    # ── 方案 2: workflow 尚未實作，返回 None ──
    return None


def aggregate(records: list[dict]) -> dict:
    """彙總多筆 execution 的「19.是否有其他問題」數據。"""
    valid = [r for r in records if r is not None]

    no_other = sum(1 for r in valid if r.get("response_type") == "no_other_question")
    has_card = sum(1 for r in valid if r.get("response_type") == "has_card_question")
    has_bank = sum(1 for r in valid if r.get("response_type") == "has_bank_question")

    result = {
        "report_item": "19.是否有其他問題",
        "total_count": len(valid),
        "no_other_question_count": no_other,
        "has_card_question_count": has_card,
        "has_bank_question_count": has_bank,
    }

    # 停留時間統計
    stay_records = [r for r in valid if r.get("stay_duration_sec") is not None]
    if stay_records:
        total_stay = sum(r["stay_duration_sec"] for r in stay_records)
        result["avg_stay_duration_sec"] = round(total_stay / len(stay_records), 3)

    # 如果都是 0 筆，加上提示
    if not valid:
        result["note"] = "workflow 尚未實作此節點，目前無資料"

    return result