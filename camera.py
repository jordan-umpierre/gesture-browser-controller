"""Optional local camera adapter; frames are consumed and discarded in memory."""

from __future__ import annotations

from collections.abc import Callable

from controller import GestureObservation, GestureRecognizer


def run_camera(on_observation: Callable[[GestureObservation], None], recognizer: GestureRecognizer) -> None:
    try:
        import cv2
        import mediapipe as mp
    except ImportError as error:
        raise RuntimeError("camera mode requires optional opencv-python and mediapipe packages") from error
    capture = cv2.VideoCapture(0)
    if not capture.isOpened():
        raise RuntimeError("camera permission was denied or no camera is available")
    hands = mp.solutions.hands.Hands(max_num_hands=1, min_detection_confidence=recognizer.profile.confidence_threshold)
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError("camera frame capture failed")
            result = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if result.multi_hand_landmarks:
                points = [(point.x, point.y) for point in result.multi_hand_landmarks[0].landmark]
                observation = recognizer.recognize(points, recognizer.profile.confidence_threshold)
                if observation:
                    on_observation(observation)
            if cv2.waitKey(1) & 0xFF == 27:
                break
    finally:
        hands.close()
        capture.release()
        cv2.destroyAllWindows()
