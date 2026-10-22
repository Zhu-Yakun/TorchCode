from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

# Add the root directory to PYTHONPATH so we can import torch_judge
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from torch_judge.tasks import TASKS, get_task
from torch_judge.web_engine import execute_code
from api.parser import get_all_templates

app = FastAPI(title="TorchCode UI Backend")

# Allow CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load templates on startup
TEMPLATES = get_all_templates()
ANSWERS_DIR = Path(__file__).resolve().parent.parent / "MyAnswer"


def save_accepted_answer(task_id: str, code: str) -> Path:
    task = get_task(task_id)
    filename = f"{task['title']} ({task.get('difficulty', 'Unknown')}).py"
    # Some titles contain characters Windows does not allow in filenames.
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
    ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
    answer_path = ANSWERS_DIR / filename
    temporary_path = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=ANSWERS_DIR, suffix=".tmp", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(code)
        # Replace only after the complete source has been written successfully.
        temporary_path.replace(answer_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return answer_path

class SubmitRequest(BaseModel):
    code: str

@app.get("/api/tasks")
def list_tasks():
    tasks_list = []
    for task_id, task_data in TASKS.items():
        tasks_list.append({
            "id": task_id,
            "title": task_data["title"],
            "difficulty": task_data.get("difficulty", "Unknown")
        })
    return tasks_list

@app.get("/api/tasks/{task_id}")
def get_task_details(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    template = TEMPLATES.get(task_id, {})
    return {
        "id": task_id,
        "title": task["title"],
        "difficulty": task.get("difficulty", "Unknown"),
        "hint": task.get("hint", ""),
        "description": template.get("description", "Description not found."),
        "initial_code": template.get("initial_code", "# Write your code here.")
    }

@app.post("/api/submit/{task_id}")
def submit_code(task_id: str, request: SubmitRequest):
    result = execute_code(task_id, request.code)
    if result["success"]:
        try:
            result["saved_file"] = str(save_accepted_answer(task_id, request.code))
        except OSError as exc:
            # Keep the Accepted result, and show the save failure in the existing error panel.
            result["error"] = f"Code accepted, but saving to MyAnswer failed: {exc}"
    return result
