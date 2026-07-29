# match_data.py

from datetime import datetime, timedelta
from time import sleep
from zoneinfo import ZoneInfo

import requests

from config import FOOTBALL_API_KEY


BASE_URL = "https://v3.football.api-sports.io"
TIMEZONE = "Asia/Taipei"

HEADERS = {
    "x-apisports-key": FOOTBALL_API_KEY
}


def call_api(endpoint, params=None):
    """
    統一呼叫 API-Football。
    成功時回傳 API 的 response list。
    失敗時丟出清楚的 RuntimeError。
    """

    url = f"{BASE_URL}/{endpoint}"

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            params=params,
            timeout=15
        )

        response.raise_for_status()
        data = response.json()

    except requests.Timeout as error:
        raise RuntimeError("Football API 連線逾時。") from error

    except requests.ConnectionError as error:
        raise RuntimeError("無法連上 Football API，請檢查網路。") from error

    except requests.RequestException as error:
        raise RuntimeError(f"Football API HTTP 錯誤：{error}") from error

    except ValueError as error:
        raise RuntimeError("Football API 回傳的內容不是有效 JSON。") from error

    errors = data.get("errors")

    if errors:
        raise RuntimeError(f"Football API 錯誤：{errors}")

    return data.get("response", [])


def get_match_day():
    """
    取得程式使用的比賽日。
    """

    now = datetime.now(ZoneInfo(TIMEZONE))

    return now.date().isoformat()


def format_fixture(item):
    """
    把 API 原始 fixture 整理成專案統一格式。
    """

    fixture = item["fixture"]
    league = item["league"]
    teams = item["teams"]
    goals = item["goals"]
    score = item["score"]

    home = teams["home"]["name"]
    away = teams["away"]["name"]

    home_score = goals["home"]
    away_score = goals["away"]

    status = fixture["status"]
    elapsed = status["elapsed"]

    # 尚未開賽時比分可能是 None
    if home_score is None:
        home_score = 0

    if away_score is None:
        away_score = 0

    kickoff = datetime.fromisoformat(fixture["date"])

    line1 = (
        f"{home[:3].upper()} "
        f"{home_score}-{away_score} "
        f"{away[:3].upper()}"
    )[:16]

    if elapsed is None:
        line2 = status["short"][:16]
    else:
        line2 = f"{elapsed}' {status['short']}"[:16]

    return {
        "fixture_id": fixture["id"],
        "home": home,
        "away": away,
        "home_score": home_score,
        "away_score": away_score,
        "kickoff_time": fixture["date"],
        "kickoff_display": kickoff.strftime("%H:%M"),
        "status_short": status["short"],
        "status_long": status["long"],
        "elapsed": elapsed,
        "league": league["name"],
        "round": league["round"],
        "halftime": score["halftime"],
        "fulltime": score["fulltime"],
        "extratime": score["extratime"],
        "penalty": score["penalty"],
        "display": (
            f"{kickoff.strftime('%H:%M')} "
            f"{home} vs {away}"
        ),
        "line1": line1,
        "line2": line2
    }


def get_matches_by_date(match_date=None):
    """
    抓指定比賽日所有可存取的比賽。


    """

    if match_date is None:
        match_date = get_match_day()

    response_items = call_api(
        endpoint="fixtures",
        params={
            "date": match_date,
            "timezone": TIMEZONE
        }
    )

    matches = [
        format_fixture(item)
        for item in response_items
    ]

    matches.sort(key=lambda match: match["kickoff_time"])

    return matches


def find_match_by_teams(
    home_team,
    away_team,
    match_date=None
):
    """
    依主客隊名稱搜尋指定比賽。

    名稱不用分大小寫。
    若 API 主客順序相反，也會嘗試找出。
    """

    matches = get_matches_by_date(match_date)

    target_home = home_team.strip().lower()
    target_away = away_team.strip().lower()

    for match in matches:
        home = match["home"].lower()
        away = match["away"].lower()

        normal_order = (
            target_home in home
            and target_away in away
        )

        reverse_order = (
            target_home in away
            and target_away in home
        )

        if normal_order or reverse_order:
            return match

    return None


def get_match_data(fixture_id):
    """
    以 fixture_id 取得單場最新比分與狀態。
    這是比賽中定期輪詢時主要使用的函式。
    """

    response_items = call_api(
        endpoint="fixtures",
        params={
            "id": fixture_id,
            "timezone": TIMEZONE
        }
    )

    if not response_items:
        return None

    return format_fixture(response_items[0])


def get_match_events(fixture_id):
    """
    抓單場事件：
    進球、黃牌、紅牌、換人、VAR 等。
    """

    response_items = call_api(
        endpoint="fixtures/events",
        params={
            "fixture": fixture_id
        }
    )

    events = []

    for item in response_items:
        elapsed = item["time"]["elapsed"]
        extra = item["time"].get("extra")

        if extra is None:
            time_text = f"{elapsed}'"
        else:
            time_text = f"{elapsed}+{extra}'"

        player = item.get("player") or {}
        assist = item.get("assist") or {}
        team = item.get("team") or {}

        events.append({
            "time": time_text,
            "minute": elapsed,
            "extra": extra,
            "team": team.get("name"),
            "player": player.get("name"),
            "assist": assist.get("name"),
            "type": item.get("type"),
            "detail": item.get("detail"),
            "comments": item.get("comments")
        })

    return events


def get_match_statistics(fixture_id):
    """
    抓控球率、射門、角球等統計。
    回傳格式為：
    {
        "France": {
            "Ball Possession": "55%",
            ...
        }
    }
    """

    response_items = call_api(
        endpoint="fixtures/statistics",
        params={
            "fixture": fixture_id
        }
    )

    result = {}

    for team_item in response_items:
        team_name = team_item["team"]["name"]
        team_stats = {}

        for stat in team_item["statistics"]:
            team_stats[stat["type"]] = stat["value"]

        result[team_name] = team_stats

    return result


def print_match(match):
    """
    測試用：清楚印出一場比賽。
    """

    if match is None:
        print("找不到比賽。")
        return

    print("\n========== Match ==========")
    print("Fixture ID :", match["fixture_id"])
    print("Competition:", match["league"])
    print("Round      :", match["round"])
    print("Kickoff    :", match["kickoff_time"])
    print("Match      :", match["home"], "vs", match["away"])
    print(
        "Score      :",
        match["home_score"],
        "-",
        match["away_score"]
    )
    print("Status     :", match["status_long"])
    print("Elapsed    :", match["elapsed"])
    print("LCD line 1 :", match["line1"])
    print("LCD line 2 :", match["line2"])


def watch_match_live(
    fixture_id,
    interval_seconds=60,
    max_updates=None
):
    """
    定期更新指定比賽。

    interval_seconds：


    max_updates：
    測試時限制查詢次數。
    None 代表直到比賽結束或手動 Ctrl+C。
    """

    previous_score = None
    previous_status = None
    previous_event_count = 0
    update_count = 0

    finished_statuses = {
        "FT",   # Full Time
        "AET",  # After Extra Time
        "PEN",  # After Penalties
        "CANC",
        "ABD",
        "AWD",
        "WO"
    }

    print("\n開始追蹤比賽。按 Ctrl+C 可停止。")

    try:
        while True:
            match = get_match_data(fixture_id)

            if match is None:
                print("查不到這場比賽。")
                return

            current_score = (
                match["home_score"],
                match["away_score"]
            )

            current_status = match["status_short"]

            print(
                f"{match['home']} "
                f"{match['home_score']}-"
                f"{match['away_score']} "
                f"{match['away']} | "
                f"{match['line2']}"
            )

            # 比分改變
            if (
                previous_score is not None
                and current_score != previous_score
            ):
                print("⚽ 比分發生變化！")

            # 狀態改變，例如 NS -> 1H -> HT -> 2H -> FT
            if (
                previous_status is not None
                and current_status != previous_status
            ):
                print(
                    "狀態改變：",
                    previous_status,
                    "->",
                    current_status
                )

            # 取得事件並檢查是否新增
            events = get_match_events(fixture_id)

            if len(events) > previous_event_count:
                new_events = events[previous_event_count:]

                print("新增事件：")

                for event in new_events:
                    print(
                        event["time"],
                        event["team"],
                        event["player"],
                        event["type"],
                        event["detail"]
                    )

            previous_score = current_score
            previous_status = current_status
            previous_event_count = len(events)

            update_count += 1

            if current_status in finished_statuses:
                print("比賽已結束，停止更新。")
                break

            if (
                max_updates is not None
                and update_count >= max_updates
            ):
                print("已到測試次數上限。")
                break

            sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\n使用者停止追蹤。")


if __name__ == "__main__":
    # 明天凌晨測西班牙 vs 比利時時，
    # 用你的「比賽日」規則搜尋。
    match = find_match_by_teams(
        home_team="Oakleigh Cannons",
        away_team="Avondale"
    )

    print_match(match)

    if match is not None:

        # 成功後可把 max_updates 改成 None。
        watch_match_live(
            fixture_id=match["fixture_id"],
            interval_seconds=60,
            max_updates=3
        )
    # matches = get_matches_by_date()

    # print(len(matches))

    # for m in matches:
    #     print(m["home"], "vs", m["away"])
