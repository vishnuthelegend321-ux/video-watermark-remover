import os
import shutil
import uuid
from typing import List
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse

from config import UPLOAD_DIR, PROCESSED_DIR, ALLOWED_EXTENSIONS
from database import (
    init_db, create_batch, create_task, get_batch_tasks,
    get_task, get_all_batches
)
from queue_worker import worker

app = FastAPI(title="AI Video Watermark Remover Core")

@app.on_event("startup")
def startup_event():
    init_db()
    worker.start()

@app.on_event("shutdown")
def shutdown_event():
    worker.stop()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    templates_path = Path(__file__).resolve().parent / "templates" / "index.html"
    with open(templates_path, "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/upload")
async def upload_batch(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No video files uploaded.")

    valid_files = [f for f in files if os.path.splitext(f.filename)[1].lower() in ALLOWED_EXTENSIONS]

    if not valid_files:
        raise HTTPException(status_code=400, detail="No valid video formats uploaded.")

    batch_id = create_batch(total_videos=len(valid_files))
    created_tasks = []

    for file in valid_files:
        prefix = str(uuid.uuid4())[:8]
        safe_filename = f"{prefix}_{file.filename}"
        input_path = UPLOAD_DIR / safe_filename
        output_path = PROCESSED_DIR / f"clean_{safe_filename}"

        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        task_id = create_task(
            batch_id=batch_id,
            filename=file.filename,
            input_path=str(input_path),
            output_path=str(output_path)
        )
        created_tasks.append({"task_id": task_id, "filename": file.filename, "status": "queued"})

    return {
        "success": True,
        "batch_id": batch_id,
        "total_videos": len(valid_files),
        "tasks": created_tasks
    }

@app.get("/api/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    tasks = get_batch_tasks(batch_id)
    if not tasks:
        raise HTTPException(status_code=404, detail="Batch ID not found.")

    total = len(tasks)
    completed = sum(1 for t in tasks if t["status"] == "completed")
    processing = sum(1 for t in tasks if t["status"] == "processing")
    queued = sum(1 for t in tasks if t["status"] == "queued")
    failed = sum(1 for t in tasks if t["status"] == "failed")
    progress = round((sum(t["progress"] for t in tasks) / (total * 100)) * 100, 1) if total > 0 else 0

    return {
        "batch_id": batch_id,
        "total_videos": total,
        "stats": {"completed": completed, "processing": processing, "queued": queued, "failed": failed, "overall_progress": progress},
        "tasks": tasks
    }

@app.get("/api/batches")
async def list_recent_batches():
    return {"batches": get_all_batches()}

@app.get("/api/download/{task_id}")
async def download_video(task_id: str):
    task = get_task(task_id)
    if not task or task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video not ready for download.")

    output_path = task["output_path"]
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Processed video file not found.")

    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        filename=f"clean_{task['filename']}"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
