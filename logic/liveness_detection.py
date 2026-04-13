import cv2
import numpy as np
from collections import deque
import os
try:
    from dl_liveness import DeepTextureLiveness
except ImportError:
    from logic.dl_liveness import DeepTextureLiveness

class LivenessDetector:
    """
    Liveness detection using Multi-Stage Verification:
    1. Texture Analysis (Deep Learning - MiniFASNet)
    2. Head Turn Tracking (MTCNN Landmarks)
    3. Eye Blink Detection (Haar Cascade)
    """

    def __init__(self):
        # ── Head Turn Configuration ──
        self.turn_threshold_low = 0.60
        self.turn_threshold_high = 1.6
        
        # ── Blink Detection Configuration ──
        cv2_data_path = cv2.data.haarcascades
        self.eye_cascade = cv2.CascadeClassifier(cv2_data_path + 'haarcascade_eye.xml')
        self.eye_history = deque(maxlen=30)
        self.blinks_detected = 0
        self.eyes_were_closed = False
        self.consecutive_open = 0
        self.consecutive_closed = 0
        self.min_open_before_blink = 2
        self.min_closed_frames = 1
        self.max_closed_frames = 5
        self.required_blinks = 1
        self.open_count_at_close_start = 0

        # Face size tracking (anti-spoof for blinks)
        self.face_size_history = deque(maxlen=15)
        self.max_face_size_change = 0.30

        # ── State ──
        self.is_confirmed_live = False
        self.frames_processed = 0
        self.has_turned_left = False
        self.has_turned_right = False
        self.liveness_method = None # "Head Turn", "Blink", or "DL-Texture"
        
        # ── Deep Learning Texture Analysis ──
        logic_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(logic_dir, "..", "models", "liveness_model.pth")
        self.dl_detector = DeepTextureLiveness(model_path=model_path)

        # ── Debug ──
        self.debug_values = {}

    def _calculate_eye_nose_ratio(self, landmarks):
        if len(landmarks) < 3: return 1.0
        left_eye, right_eye, nose = np.array(landmarks[0]), np.array(landmarks[1]), np.array(landmarks[2])
        dist_left_to_nose = np.linalg.norm(nose - left_eye)
        dist_right_to_nose = np.linalg.norm(nose - right_eye)
        return dist_left_to_nose / dist_right_to_nose if dist_right_to_nose != 0 else 1.0

    def _detect_eyes_in_face(self, frame, face_box):
        x1, y1, x2, y2 = map(int, face_box)
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
        face_w, face_h = x2 - x1, y2 - y1
        if face_h < 30: return 0
        upper_face = frame[y1 : y1 + face_h // 2, x1 : x2]
        if upper_face.size == 0: return 0
        gray = cv2.cvtColor(upper_face, cv2.COLOR_BGR2GRAY)
        eyes = self.eye_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(20, 20))
        return min(len(eyes), 2)

    def _is_face_size_stable(self):
        if len(self.face_size_history) < 3: return True
        recent = list(self.face_size_history)
        check_frames = recent[-min(5, len(recent)):]
        min_area, max_area = min(check_frames), max(check_frames)
        if min_area == 0: return False
        change_ratio = (max_area - min_area) / min_area
        self.debug_values['face_change'] = change_ratio
        return change_ratio < self.max_face_size_change

    def check_liveness(self, frame, face_boxes, landmarks_list=None):
        if not face_boxes:
            return {'is_live': self.is_confirmed_live, 'reason': 'No face detected', 'blinks': self.blinks_detected, 'eyes_detected': 0, 'debug_text': ''}

        self.frames_processed += 1
        face_box = face_boxes[0]
        
        # ── 1. Texture Check (Primary Defense) ──
        texture_score = 0.0
        if self.dl_detector:
            texture_score, _ = self.dl_detector.predict(frame, face_box)
            self.debug_values['dl_score'] = texture_score

        # ── 2. Active Checks (Secondary Layer) ──
        # Head Turn Logic
        if landmarks_list and len(landmarks_list) > 0:
            ratio = self._calculate_eye_nose_ratio(landmarks_list[0])
            self.debug_values['ratio'] = ratio
            if ratio < self.turn_threshold_low: self.has_turned_right = True
            elif ratio > self.turn_threshold_high: self.has_turned_left = True

        # Blink Logic
        x1, y1, x2, y2 = map(int, face_box)
        self.face_size_history.append(max(0, (x2 - x1) * (y2 - y1)))
        eyes_count = self._detect_eyes_in_face(frame, face_box)
        self.eye_history.append(eyes_count)
        if eyes_count >= 2:
            self.consecutive_open += 1
            if self.eyes_were_closed and self.open_count_at_close_start >= self.min_open_before_blink and self.consecutive_closed <= self.max_closed_frames and self._is_face_size_stable():
                self.blinks_detected += 1
            self.consecutive_closed, self.eyes_were_closed = 0, False
        else:
            if not self.eyes_were_closed: self.open_count_at_close_start = self.consecutive_open
            self.consecutive_closed += 1
            self.consecutive_open, self.eyes_were_closed = 0, True

        # ── 3. Hybrid Confirmation Logic ──
        # We REJECT if texture analysis says it's definitely a spoof
        if texture_score < 0.3:
            self.reset_partially()
            reason = "SPOOF DETECTED (Screen/Photo)"
        
        elif not self.is_confirmed_live:
            # Case A: High-confidence Real Texture
            if texture_score > 0.98:
                self.is_confirmed_live = True
                self.liveness_method = "DL-Texture"
            
            # Case B: Action + Confident Texture
            elif texture_score > 0.6:
                if self.has_turned_left or self.has_turned_right:
                    self.is_confirmed_live = True
                    self.liveness_method = "Head Turn"
                elif self.blinks_detected >= self.required_blinks:
                    self.is_confirmed_live = True
                    self.liveness_method = "Blink"
            
            reason = "Turn head OR Blink to verify"
        
        if self.is_confirmed_live:
            reason = f"LIVE - {self.liveness_method} confirmed!"

        debug_text = f"DL: {texture_score:.2f} | B: {self.blinks_detected} | R: {self.debug_values.get('ratio', 1.0):.2f}"
        return {'is_live': self.is_confirmed_live, 'reason': reason, 'blinks': self.blinks_detected, 'eyes_detected': eyes_count, 'debug_text': debug_text}

    def reset_partially(self):
        self.has_turned_left = False
        self.has_turned_right = False
        self.blinks_detected = 0

    def reset(self):
        self.is_confirmed_live = False
        self.frames_processed = 0
        self.has_turned_left = False
        self.has_turned_right = False
        self.liveness_method = None
        self.blinks_detected = 0
        self.eyes_were_closed = False
        self.consecutive_open = 0
        self.consecutive_closed = 0
        self.open_count_at_close_start = 0
        self.eye_history.clear()
        self.face_size_history.clear()
        self.debug_values = {}

    def get_status_text(self):
        if self.is_confirmed_live: return f"Live Confirmed ({self.liveness_method})"
        score = self.debug_values.get('dl_score', 0.0)
        return f"Real Score: {score:.2f} | Need Action"

if __name__ == "__main__":
    detector = LivenessDetector()
    print("[OK] LivenessDetector with Hybrid Security Initialized!")
