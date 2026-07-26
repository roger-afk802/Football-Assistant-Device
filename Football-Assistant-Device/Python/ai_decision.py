# ai_decision.py

from typing import Literal

from openai import OpenAI
from pydantic import BaseModel

from config import OPENAI_API_KEY


client = OpenAI(api_key=OPENAI_API_KEY)


class AIDecision(BaseModel):
    decision: Literal["WATCH", "KEY_MOMENTS", "REST"]
    reason: str
    line1: str
    line2: str
    sound: Literal["none", "warning", "relax"]
    motor: bool
    led: Literal["green", "yellow", "red"]


def get_ai_decision(
    match_data: dict,
    focus_data: dict,
    event_time: str,
    event_name: str
) -> dict:
    """
    根據比賽、專注度與隔天行程，
    回傳觀看建議與硬體控制資料。
    """

    prompt = f"""
你是 World Cup Guardian，負責幫使用者判斷是否應繼續看球。

比賽資料：
- 比賽：{match_data.get("home")} vs {match_data.get("away")}
- 比分：{match_data.get("home_score")}-{match_data.get("away_score")}
- 分鐘：{match_data.get("elapsed")}
- 狀態：{match_data.get("status_long")}

使用者狀態：
- 專注度：{focus_data.get("focus_score")}
- 專注狀態：{focus_data.get("status")}

隔天行程：
- 時間：{event_time}
- 名稱：{event_name}

判斷規則：
1. WATCH：可以繼續看。
2. KEY_MOMENTS：只建議看關鍵時刻。
3. REST：建議休息。
4. 明早行程越早，越應提高休息優先度。
5. 專注度越低，越應傾向 KEY_MOMENTS 或 REST。
6. 若比賽接近尾聲且比分接近，可提高觀看優先度。
7. line1、line2 必須是英文 ASCII，且各自最多 16 個字元。
8. green 對應 WATCH，yellow 對應 KEY_MOMENTS，red 對應 REST。
9. sound 只能是：
   - none：不播放音效
   - warning：需要提醒使用者注意或只看關鍵時刻
   - relax：建議休息
10. motor 只在重要提醒時開啟。
"""

    response = client.responses.parse(
        model="gpt-5-mini",
        input=[
            {
                "role": "system",
                "content": (
                    "You are a concise football viewing and sleep decision system."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        text_format=AIDecision
    )

    result = response.output_parsed

    if result is None:
        raise RuntimeError("GPT 沒有回傳有效決策。")

    return {
        "decision": result.decision,
        "reason": result.reason,
        "line1": result.line1[:16],
        "line2": result.line2[:16],
        "sound": result.sound,
        "motor": result.motor,
        "led": result.led
    }


if __name__ == "__main__":
    fake_match = {
        "home": "Spain",
        "away": "Belgium",
        "home_score": 1,
        "away_score": 1,
        "elapsed": 82,
        "status_long": "Second Half"
    }

    fake_focus = {
        "focus_score": 38,
        "status": "tired_or_distracted"
    }

    decision = get_ai_decision(
        match_data=fake_match,
        focus_data=fake_focus,
        event_time="08:00",
        event_name="Class"
    )

    print(decision)