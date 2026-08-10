import time
import threading
import logging
from database import get_next_queued_task, update_task_status
from watermark_remover import remove_watermark_from_video

class VideoProcessingWorker:
    def __init__(self, poll_interval=2.0):
        self.poll_interval = poll_interval
        self._running = False
        self._thread = None

    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)

    def _run_loop(self):
        while self._running:
            try:
                task = get_next_queued_task()
                if task:
                    self._process_task(task)
                else:
                    time.sleep(self.poll_interval)
            except Exception:
                time.sleep(self.poll_interval)

    def _process_task(self, task: dict):
        task_id = task["task_id"]
        update_task_status(task_id, status="processing", progress=0.0)

        def progress_cb(current, total, percent):
            update_task_status(task_id, status="processing", progress=percent)

        try:
            remove_watermark_from_video(
                input_path=task["input_path"],
                output_path=task["output_path"],
                progress_callback=progress_cb
            )
            update_task_status(task_id, status="completed", progress=100.0)
        except Exception as e:
            update_task_status(task_id, status="failed", error_message=str(e))

worker = VideoProcessingWorker()