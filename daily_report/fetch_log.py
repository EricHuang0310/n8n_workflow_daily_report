"""
fetch_log.py - 從 n8n REST API 抓取指定日期的 execution log
=============================================================

n8n 公開 API 的 /executions 端點沒有日期區間參數，但預設依時間倒序排列。
本模組分頁拉取，遇到早於目標日期的 execution 就停止，避免抓全部歷史紀錄。

環境變數:
  N8N_BASE_URL   例如: https://n8n.example.com
  N8N_API_KEY    n8n 的 Personal API Key (X-N8N-API-KEY header)
  N8N_WORKFLOW_ID  (選用) 只抓特定 workflow

使用方式:
  python fetch_log.py [--date YYYY-MM-DD] [--workflow-id <id>] [--output <path>]

預設行為:
  - --date 未指定 → 抓取「昨天」(台北時間) 的 executions
  - --output 未指定 → executions_YYYYMMDD.json (台北日期)
  - 日期範圍以台北時間 (UTC+8) 為準
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

TAIPEI_TZ = timezone(timedelta(hours=8))
PAGE_LIMIT = 100  # n8n REST API 最大值通常為 250；100 較保守


def _today_taipei() -> date:
    return datetime.now(TAIPEI_TZ).date()


def _parse_date_arg(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _to_taipei_date(iso_str: str) -> date | None:
    """把 n8n 回傳的 startedAt (UTC ISO 字串) 轉成台北日期。"""
    if not iso_str:
        return None
    try:
        # 接受 ...Z 或 +00:00
        s = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(TAIPEI_TZ).date()
    except Exception:
        return None


def _http_get(url: str, headers: dict, retries: int = 3) -> dict:
    last_exc = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # 4xx 直接拋,5xx 才重試
            if 400 <= e.code < 500:
                raise
            last_exc = e
        except (urllib.error.URLError, TimeoutError) as e:
            last_exc = e
        time.sleep(2 ** attempt)
    raise RuntimeError(f"HTTP GET 失敗: {url} 錯誤: {last_exc}")


def fetch_executions_for_date(
    base_url: str,
    api_key: str,
    target_date: date,
    workflow_id: str | None = None,
    page_limit: int = PAGE_LIMIT,
) -> list[dict]:
    """
    分頁抓取 executions, 直到看到早於 target_date 的紀錄就停止。
    回傳 startedAt 的台北日期 == target_date 的 execution 清單。
    """
    base_url = base_url.rstrip("/")
    headers = {
        "X-N8N-API-KEY": api_key,
        "Accept": "application/json",
    }

    collected: list[dict] = []
    cursor: str | None = None
    page = 0
    seen_older = False

    while True:
        page += 1
        params = {
            "limit": str(page_limit),
            "includeData": "true",
        }
        if workflow_id:
            params["workflowId"] = workflow_id
        if cursor:
            params["cursor"] = cursor

        url = f"{base_url}/api/v1/executions?{urllib.parse.urlencode(params)}"
        payload = _http_get(url, headers)

        items = payload.get("data") or []
        if not items:
            break

        page_kept = 0
        for ex in items:
            started_d = _to_taipei_date(ex.get("startedAt") or "")
            if started_d is None:
                # 沒 startedAt 的稀有情況: 略過
                continue
            if started_d > target_date:
                # 比目標日新, 跳過
                continue
            if started_d < target_date:
                # 已經看到更舊的, 後面都更舊 → 停
                seen_older = True
                continue
            collected.append(ex)
            page_kept += 1

        last_started = _to_taipei_date(items[-1].get("startedAt") or "")
        print(
            f"  [page {page}] 取回 {len(items)} 筆, 命中目標日 {page_kept} 筆, "
            f"末筆台北日期 {last_started}"
        )

        if seen_older:
            break

        cursor = payload.get("nextCursor")
        if not cursor:
            break

    return collected


def main():
    args = sys.argv[1:]
    target_date_str: str | None = None
    workflow_id: str | None = os.environ.get("N8N_WORKFLOW_ID")
    output_path: str | None = None

    i = 0
    while i < len(args):
        if args[i] == "--date" and i + 1 < len(args):
            target_date_str = args[i + 1]
            i += 2
        elif args[i] == "--workflow-id" and i + 1 < len(args):
            workflow_id = args[i + 1]
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output_path = args[i + 1]
            i += 2
        else:
            i += 1

    base_url = os.environ.get("N8N_BASE_URL")
    api_key = os.environ.get("N8N_API_KEY")
    if not base_url or not api_key:
        print("錯誤: 請先設定環境變數 N8N_BASE_URL 與 N8N_API_KEY")
        sys.exit(2)

    target_date = (
        _parse_date_arg(target_date_str)
        if target_date_str
        else (_today_taipei() - timedelta(days=1))
    )
    if output_path is None:
        output_path = f"executions_{target_date.strftime('%Y%m%d')}.json"

    print(f"[FetchLog] 目標日期 (台北時間): {target_date}")
    print(f"[FetchLog] base_url = {base_url}")
    if workflow_id:
        print(f"[FetchLog] workflow_id = {workflow_id}")

    executions = fetch_executions_for_date(
        base_url=base_url,
        api_key=api_key,
        target_date=target_date,
        workflow_id=workflow_id,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"data": executions}, f, ensure_ascii=False)

    print(f"[FetchLog] 共寫入 {len(executions)} 筆 execution → {output_path}")


if __name__ == "__main__":
    main()
