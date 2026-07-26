# main.py

import time

from match_data import (
    get_matches_by_date,
    get_match_data,
    get_match_events
)
from user_input_gui import get_user_settings
from camera_focus import get_focus_data
from ai_decision import get_ai_decision
from esp32_client import send_to_esp32


# =====================================================
# 執行頻率設定
# =====================================================

# 每 2 分鐘取得一次最新比賽資料
FOOTBALL_INTERVAL = 120

# 每 5 分鐘檢查一次使用者專注狀態
CAMERA_INTERVAL = 300

CAMERA_DURATION = 5
GPT_MAX_INTERVAL = 300

# 主迴圈每秒檢查一次
MAIN_LOOP_INTERVAL = 1

# 外接鏡頭
CAMERA_INDEX = 1

TEMP_DISPLAY_SECONDS = 5

# 比賽結束或無法繼續追蹤的狀態
FINISHED_STATUSES = {
    "FT",
    "AET",
    "PEN",
    "CANC",
    "ABD",
    "AWD",
    "WO"
}


# =====================================================
# LCD / ESP32 資料處理
# =====================================================

def lcd_text(value) -> str:
    """
    將任何資料轉成字串，並限制在 LCD 的 16 個字元內。
    """
    if value is None:
        return ""

    return str(value)[:16]


def send_display(
    line1: str,
    line2: str,
    led: str = "off",
    servo: str = "none",
    sound: str = "none"
) -> bool:
    """
    統一將資料傳送至 ESP32。
    """

    data = {
        "line1": lcd_text(line1),
        "line2": lcd_text(line2),
        "led": led,
        "servo": servo,
        "sound": sound
    }

    print("\n傳送到 ESP32：", data)

    return send_to_esp32(data)


def send_match_display(match_data: dict, led: str = "off") -> bool:
    """
    將目前比賽資料顯示在 LCD。
    """

    return send_display(
        line1=match_data.get("line1", "Match"),
        line2=match_data.get("line2", ""),
        led=led,
        servo="none",
        sound="none"
    )


def show_temporary_display(
    line1: str,
    line2: str,
    match_data: dict,
    led: str,
    current_match_led: str,
    servo: str = "none",
    sound: str = "none",
    seconds: int = TEMP_DISPLAY_SECONDS
):
    """
    顯示臨時資訊數秒，之後恢復比賽畫面。
    """

    send_display(
        line1=line1,
        line2=line2,
        led=led,
        servo=servo,
        sound=sound
    )

    time.sleep(seconds)

    send_match_display(
        match_data=match_data,
        led=current_match_led
    )


# =====================================================
# Terminal 輸出
# =====================================================

def print_match_data(match_data: dict):
    print("\n========== Match Update ==========")

    print(
        f"{match_data.get('home')} "
        f"{match_data.get('home_score')}-"
        f"{match_data.get('away_score')} "
        f"{match_data.get('away')}"
    )

    print("Minute:", match_data.get("elapsed"))
    print("Status:", match_data.get("status_short"))

    print(
        "LCD:",
        match_data.get("line1"),
        "|",
        match_data.get("line2")
    )


def print_focus_data(focus_data: dict):
    print("\n========== Focus Update ==========")
    print("Score:", focus_data.get("focus_score"))
    print("Status:", focus_data.get("status"))
    print("Face:", focus_data.get("face_detected"))
    print("Eyes:", focus_data.get("eyes_open"))
    print("Head down:", focus_data.get("head_down"))
    print("Reason:", focus_data.get("reason"))


def print_ai_decision(decision: dict):
    print("\n========== AI Decision ==========")
    print("Decision:", decision.get("decision"))
    print("Reason:", decision.get("reason"))
    print("LCD line 1:", decision.get("line1"))
    print("LCD line 2:", decision.get("line2"))
    print("Sound:", decision.get("sound"))
    print("Motor:", decision.get("motor"))
    print("LED:", decision.get("led"))


def print_new_events(events: list):
    if not events:
        return

    print("\n========== New Events ==========")

    for event in events:
        print(
            event.get("time"),
            event.get("team"),
            event.get("player"),
            event.get("type"),
            event.get("detail")
        )


# =====================================================
# 專注度畫面
# =====================================================

def get_focus_led(focus_data: dict) -> str:
    """
    根據專注分數決定臨時顯示時使用的燈色。
    """

    score = focus_data.get("focus_score", 0)

    if score >= 75:
        return "green"

    if score >= 45:
        return "yellow"

    return "red"


def show_focus_on_esp32(
    focus_data: dict,
    match_data: dict,
    current_match_led: str
):
    """
    顯示專注度 5 秒，之後恢復比賽資料。
    """

    score = focus_data.get("focus_score", 0)
    status = focus_data.get("status", "unknown")

    show_temporary_display(
        line1=f"Focus: {score}",
        line2=status,
        match_data=match_data,
        led=get_focus_led(focus_data),
        current_match_led=current_match_led
    )


# =====================================================
# GPT 建議畫面
# =====================================================

def show_ai_on_esp32(
    decision: dict,
    match_data: dict
) -> str:
    """
    顯示 GPT 建議 5 秒，之後恢復比賽畫面。

    回傳 GPT 決定的 LED 顏色，作為之後比賽畫面的固定燈色。
    """

    led = decision.get("led", "off")

    servo_action = (
        "celebrate"
        if decision.get("motor", False)
        else "none"
    )

    sound_action = decision.get("sound", "none")

    show_temporary_display(
        line1=decision.get("line1", "AI Decision"),
        line2=decision.get("line2", ""),
        match_data=match_data,
        led=led,
        current_match_led=led,
        servo=servo_action,
        sound=sound_action
    )

    return led


# =====================================================
# 比賽事件畫面
# =====================================================

def is_goal_event(event: dict) -> bool:
    event_text = " ".join([
        str(event.get("type", "")),
        str(event.get("detail", ""))
    ]).lower()

    return "goal" in event_text


def get_event_led(event: dict) -> str:
    text = " ".join([
        str(event.get("type", "")),
        str(event.get("detail", ""))
    ]).lower()

    if "goal" in text:
        return "green"

    if "red card" in text or "red" in text:
        return "red"

    return "yellow"


def show_event_on_esp32(
    event: dict,
    match_data: dict,
    current_match_led: str
):
    """
    顯示一筆比賽事件。

    若為進球：
    - 顯示 GOAL
    - Servo 執行 goal 動作
    """

    event_type = str(event.get("type", "Event"))
    detail = str(event.get("detail", ""))
    player = str(event.get("player") or "")
    team = str(event.get("team") or "")
    event_time = str(event.get("time") or "")

    goal = is_goal_event(event)

    if goal:
        line1 = f"GOAL {event_time}"
        line2 = player or team or "Goal!"
        servo_action = "goal"
        sound_action = "goal"
    else:
        line1 = f"{event_type} {event_time}"
        line2 = player or team or detail
        servo_action = "none"

        event_text = f"{event_type} {detail}".lower()

        if (
            "red card" in event_text
            or "penalty" in event_text
            or "var" in event_text
        ):
            sound_action = "event"
        else:
            sound_action = "none"

    show_temporary_display(
        line1=line1,
        line2=line2,
        match_data=match_data,
        led=get_event_led(event),
        current_match_led=current_match_led,
        servo=servo_action,
        sound=sound_action
    )


# =====================================================
# Main
# =====================================================

def main():
    print("Football Assistant starting...")

    # -------------------------------------------------
    # 1. 取得當日比賽清單
    # -------------------------------------------------

    try:
        matches = get_matches_by_date()

    except RuntimeError as error:
        print("取得比賽清單失敗：", error)
        return

    if not matches:
        print("目前沒有找到可用比賽。")
        return

    print(f"找到 {len(matches)} 場比賽。")

    # -------------------------------------------------
    # 2. GUI 取得使用者設定
    # -------------------------------------------------

    settings = get_user_settings(matches)

    if not settings:
        print("使用者取消操作。")
        return

    selected_match = settings["match"]
    event_time = settings["event_time"]
    event_name = settings["event_name"]

    fixture_id = selected_match["fixture_id"]

    print("\n使用者選擇：")
    print(selected_match["home"], "vs", selected_match["away"])
    print("隔天行程：", event_time, event_name)

    # GUI 設定完成後傳送一次
    send_display(
        line1=(
            f"{selected_match['home']} vs "
            f"{selected_match['away']}"
        ),
        line2=f"{event_time} {event_name}",
        led="blue",
        servo="none",
        sound="none"
    )

    # -------------------------------------------------
    # 3. 第一次取得比賽資料
    # -------------------------------------------------

    try:
        match_data = get_match_data(fixture_id)

    except RuntimeError as error:
        print("取得單場資料失敗：", error)
        return

    if match_data is None:
        print("找不到選取比賽的資料。")
        return

    print_match_data(match_data)

    # 初始時尚未取得 AI 建議，先使用藍燈
    current_match_led = "blue"

    # 每次取得比賽資料都傳送
    send_match_display(
        match_data=match_data,
        led=current_match_led
    )

    # -------------------------------------------------
    # 4. 第一次檢查鏡頭
    # -------------------------------------------------

    focus_data = get_focus_data(
        camera_index=CAMERA_INDEX,
        duration=CAMERA_DURATION
    )

    print_focus_data(focus_data)

    # 每次取得專注度都傳送一次
    show_focus_on_esp32(
        focus_data=focus_data,
        match_data=match_data,
        current_match_led=current_match_led
    )

    # -------------------------------------------------
    # 5. 第一次詢問 GPT
    # -------------------------------------------------

    try:
        decision = get_ai_decision(
            match_data=match_data,
            focus_data=focus_data,
            event_time=event_time,
            event_name=event_name
        )

    except Exception as error:
        print("第一次 GPT 判斷失敗：", error)
        return

    print_ai_decision(decision)

    # GPT 建議顯示 5 秒，再回比賽畫面
    current_match_led = show_ai_on_esp32(
        decision=decision,
        match_data=match_data
    )

    # -------------------------------------------------
    # 6. 記錄目前資料
    # -------------------------------------------------

    previous_score = (
        match_data.get("home_score"),
        match_data.get("away_score")
    )

    previous_status = match_data.get("status_short")
    previous_focus_status = focus_data.get("status")

    try:
        events = get_match_events(fixture_id) or []
        previous_event_count = len(events)

    except RuntimeError as error:
        print("第一次取得事件失敗：", error)
        previous_event_count = 0

    now = time.time()

    next_football_time = now + FOOTBALL_INTERVAL
    next_camera_time = now + CAMERA_INTERVAL
    next_gpt_time = now + GPT_MAX_INTERVAL

    print("\n開始持續追蹤。")
    print("按 Ctrl + C 可以停止程式。")

    # -------------------------------------------------
    # 7. 主迴圈
    # -------------------------------------------------

    try:
        while True:
            now = time.time()

            score_changed = False
            status_changed = False
            focus_changed = False

            # =========================================
            # Football API
            # =========================================

            if now >= next_football_time:
                print("\n正在更新比賽資料……")

                try:
                    new_match_data = get_match_data(fixture_id)

                    if new_match_data is not None:
                        new_score = (
                            new_match_data.get("home_score"),
                            new_match_data.get("away_score")
                        )

                        new_status = new_match_data.get(
                            "status_short"
                        )

                        score_changed = (
                            new_score != previous_score
                        )

                        status_changed = (
                            new_status != previous_status
                        )

                        match_data = new_match_data

                        print_match_data(match_data)

                        # 每次抓到比賽資料就傳送一次
                        send_match_display(
                            match_data=match_data,
                            led=current_match_led
                        )

                        if score_changed:
                            print("⚽ 比分發生變化！")

                        if status_changed:
                            print(
                                "比賽狀態改變：",
                                previous_status,
                                "->",
                                new_status
                            )

                        previous_score = new_score
                        previous_status = new_status

                        # 比分或狀態改變時查詢事件.   改
                        if score_changed or status_changed:
                            goal_event_shown = False
                            try:
                                events = (
                                    get_match_events(fixture_id)
                                    or []
                                )

                                new_events = []

                                if len(events) > previous_event_count:
                                    new_events = events[
                                        previous_event_count:
                                    ]

                                print_new_events(new_events)

                                for event in new_events:
                                    if is_goal_event(event):
                                        goal_event_shown = True

                                    show_event_on_esp32(
                                        event=event,
                                        match_data=match_data,
                                        current_match_led=(
                                            current_match_led
                                        )
                                    )
                                previous_event_count = len(events)
                            except RuntimeError as error:

                                print(

                                    "取得比賽事件失敗：",
                                    error
                                )
                                # 若比分改變，但 API 沒回傳新進球事件
                            if (
                                score_changed
                                and not goal_event_shown
                                ):
                                    show_temporary_display(
                                        line1="GOAL!",
                                        line2=(
                                            f"{match_data.get('home_score')}"
                                            "-"
                                            f"{match_data.get('away_score')}"
                                        ),
                                        match_data=match_data,
                                        led="green",
                                        current_match_led=(
                                            current_match_led
                                        ),
                                        servo="goal",
                                        sound="goal"
                                    )

                except RuntimeError as error:
                    print("更新比賽資料失敗：", error)

                next_football_time = (
                    time.time() + FOOTBALL_INTERVAL
                )

            # =========================================
            # Camera
            # =========================================

            if now >= next_camera_time:
                print("\n正在檢查使用者狀態……")

                new_focus_data = get_focus_data(
                    camera_index=CAMERA_INDEX,
                    duration=CAMERA_DURATION
                )

                new_focus_status = new_focus_data.get("status")

                focus_changed = (
                    new_focus_status != previous_focus_status
                )

                focus_data = new_focus_data

                print_focus_data(focus_data)

                # 每次取得專注度都傳送一次
                show_focus_on_esp32(
                    focus_data=focus_data,
                    match_data=match_data,
                    current_match_led=current_match_led
                )

                if focus_changed:
                    print(
                        "專注狀態改變：",
                        previous_focus_status,
                        "->",
                        new_focus_status
                    )

                previous_focus_status = new_focus_status

                next_camera_time = (
                    time.time() + CAMERA_INTERVAL
                )

            # =========================================
            # GPT
            # =========================================

            gpt_timeout = now >= next_gpt_time

            need_gpt = (
                score_changed
                or status_changed
                or focus_changed
                or gpt_timeout
            )

            if need_gpt:
                print("\n正在重新詢問 GPT……")

                try:
                    new_decision = get_ai_decision(
                        match_data=match_data,
                        focus_data=focus_data,
                        event_time=event_time,
                        event_name=event_name
                    )

                    decision = new_decision

                    print_ai_decision(decision)

                    # 每次詢問 GPT 後傳送一次建議
                    # 5 秒後恢復比賽資料
                    current_match_led = show_ai_on_esp32(
                        decision=decision,
                        match_data=match_data
                    )

                    next_gpt_time = (
                        time.time() + GPT_MAX_INTERVAL
                    )

                except Exception as error:
                    print("GPT 判斷失敗：", error)

                    # GPT 失敗，60 秒後重試
                    next_gpt_time = time.time() + 60

            # =========================================
            # 比賽結束
            # =========================================

            if (
                match_data.get("status_short")
                in FINISHED_STATUSES
            ):
                print("\n比賽已經結束，停止追蹤。")

                send_display(
                    line1="Match finished",
                    line2=(
                        f"{match_data.get('home_score')}"
                        "-"
                        f"{match_data.get('away_score')}"
                    ),
                    led="red",
                    servo="none",
                    sound="fulltime"
                )

                break

            time.sleep(MAIN_LOOP_INTERVAL)

    except KeyboardInterrupt:
        print("\n使用者手動停止程式。")

        send_display(
            line1="System stopped",
            line2="Goodbye",
            led="off",
            servo="none",
            sound="stop"
        )


if __name__ == "__main__":
    main()
