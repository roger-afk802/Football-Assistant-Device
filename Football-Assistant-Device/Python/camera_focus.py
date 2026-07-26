# camera_focus.py

import time
import cv2


def get_focus_data(camera_index=0, duration=5):
    """
    開啟鏡頭 duration 秒，估算使用者專注度。

    判斷依據：
    1. 人臉是否持續出現
    2. 眼睛是否經常被偵測到
    3. 人臉是否大致位於畫面中央
    4. 人臉是否太小，代表可能離鏡頭太遠
    """

    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        return {
            "focus_score": 0,
            "status": "camera_error",
            "face_detected": False,
            "eyes_open": False,
            "head_down": False,
            "reason": "Cannot open camera"
        }

    # OpenCV 內建人臉模型
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades
        + "haarcascade_frontalface_default.xml"
    )

    # OpenCV 內建眼睛模型
    eye_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades
        + "haarcascade_eye_tree_eyeglasses.xml"
    )

    # 確認模型成功載入
    if face_cascade.empty() or eye_cascade.empty():
        cap.release()

        return {
            "focus_score": 0,
            "status": "model_error",
            "face_detected": False,
            "eyes_open": False,
            "head_down": False,
            "reason": "Cannot load cascade models"
        }

    frame_count = 0
    face_count = 0
    eyes_count = 0
    centered_count = 0
    close_enough_count = 0

    start_time = time.time()

    while time.time() - start_time < duration:
        ret, frame = cap.read()

        if not ret:
            continue

        frame_count += 1

        # 降低解析度，讓偵測速度更快
        frame = cv2.resize(
            frame,
            None,
            fx=0.75,
            fy=0.75
        )

        frame_height, frame_width = frame.shape[:2]

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        # 增強明暗對比，改善光線不足時的偵測
        gray = cv2.equalizeHist(gray)

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)
        )

        if len(faces) == 0:
            continue

        face_count += 1

        # 如果同時偵測到多張臉，取面積最大的一張
        x, y, w, h = max(
            faces,
            key=lambda face: face[2] * face[3]
        )

        # -------------------------
        # 1. 判斷臉是否大致在中央
        # -------------------------

        face_center_x = x + w / 2
        face_center_y = y + h / 2

        frame_center_x = frame_width / 2
        frame_center_y = frame_height / 2

        horizontal_offset = abs(
            face_center_x - frame_center_x
        ) / frame_width

        vertical_offset = abs(
            face_center_y - frame_center_y
        ) / frame_height

        is_centered = (
            horizontal_offset < 0.25
            and vertical_offset < 0.30
        )

        if is_centered:
            centered_count += 1

        # -------------------------
        # 2. 判斷臉是否太小
        # -------------------------

        face_area = w * h
        frame_area = frame_width * frame_height

        face_area_ratio = face_area / frame_area

        # 臉佔畫面至少約 4%
        close_enough = face_area_ratio > 0.04

        if close_enough:
            close_enough_count += 1

        # -------------------------
        # 3. 在人臉範圍內偵測眼睛
        # -------------------------

        face_gray = gray[y:y + h, x:x + w]

        # 眼睛通常在臉部上半部
        upper_face_gray = face_gray[0:int(h * 0.65), :]

        eyes = eye_cascade.detectMultiScale(
            upper_face_gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(20, 20)
        )

        # 偵測到至少一隻眼睛就先視為眼睛可見
        if len(eyes) >= 1:
            eyes_count += 1

    cap.release()

    if frame_count == 0:
        return {
            "focus_score": 0,
            "status": "no_frame",
            "face_detected": False,
            "eyes_open": False,
            "head_down": False,
            "reason": "No frame captured"
        }

    face_ratio = face_count / frame_count

    if face_count > 0:
        eyes_ratio = eyes_count / face_count
        centered_ratio = centered_count / face_count
        close_ratio = close_enough_count / face_count
    else:
        eyes_ratio = 0
        centered_ratio = 0
        close_ratio = 0

    # 專注度加權
    focus_score = int(
        face_ratio * 45
        + eyes_ratio * 25
        + centered_ratio * 20
        + close_ratio * 10
    )

    # 防止極端狀況超過範圍
    focus_score = max(0, min(100, focus_score))

    face_detected = face_ratio >= 0.30
    eyes_open = eyes_ratio >= 0.45


    # 用臉不在中央或太小，近似表示低頭／離開
    head_down = (
        centered_ratio < 0.45
        or close_ratio < 0.40
    )

    if focus_score >= 75:
        status = "focused"
        reason = (
            "Face and eyes detected, "
            "position mostly stable"
        )

    elif focus_score >= 45:
        status = "distracted"
        reason = (
            "Face or eyes were "
            "occasionally missing"
        )

    else:
        status = "away_or_sleepy"
        reason = (
            "Face missing, eyes unclear, "
            "or position unstable"
        )

    return {
        "focus_score": focus_score,
        "status": status,
        "face_detected": face_detected,
        "eyes_open": eyes_open,
        "head_down": head_down,
        "reason": reason,

        # 除錯用數據
        "face_ratio": round(face_ratio, 2),
        "eyes_ratio": round(eyes_ratio, 2),
        "centered_ratio": round(centered_ratio, 2),
        "close_ratio": round(close_ratio, 2),
        "frame_count": frame_count
    }


def call_camera_focus():
    return get_focus_data(
        camera_index=1,
        duration=5
    )


if __name__ == "__main__":
    result = get_focus_data(
        camera_index=1,
        duration=5
    )

    print(result)