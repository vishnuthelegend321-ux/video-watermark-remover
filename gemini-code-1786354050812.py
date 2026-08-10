import cv2
import numpy as np
import os
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WatermarkRemover")

class Inpainter:
    def __init__(self, model_version="v2-core"):
        self.model_version = model_version

    @classmethod
    def load(cls, model_version="v2-core"):
        return cls(model_version=model_version)

    def detect_watermark(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        pad_h, pad_w = int(h * 0.15), int(w * 0.20)
        mask[h - pad_h - 10 : h - 10, w - pad_w - 10 : w - 10] = 255
        return mask

    def inpaint(self, frame: np.ndarray, mask: np.ndarray) -> np.ndarray:
        if mask is None or np.sum(mask) == 0:
            return frame
        return cv2.inpaint(frame, mask, inpaintRadius=2, flags=cv2.INPAINT_TELEA)

def remove_watermark_from_video(input_path: str, output_path: str, progress_callback=None):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    model = Inpainter.load("v2-core")
    cap = cv2.VideoCapture(input_path)
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    processed_frames = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            mask = model.detect_watermark(frame)
            clean_frame = model.inpaint(frame, mask)
            out.write(clean_frame)
            processed_frames += 1

            if progress_callback and total_frames > 0 and processed_frames % 5 == 0:
                percent = min(100.0, round((processed_frames / total_frames) * 100, 2))
                progress_callback(processed_frames, total_frames, percent)

    finally:
        cap.release()
        out.release()

    return output_path