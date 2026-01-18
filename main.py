from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal


app = FastAPI(title="ToDo v1 (in-memory)")

TaskStatus = Literal["в процессе", "выполнено", "отменена"]

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)

class TaskPatch(BaseModel):
    title: str | None =Field(default=None, min_length=1, max_length=120)
    description: str |None = Field(default=None, max_length=500)
    status: TaskStatus | None = None
    
class TaskOut(BaseModel):
    id: int
    title: str
    description: str | None 
    status: TaskStatus 
    created_at: datetime
    updated_at: datetime

tasks: dict[int, dict] = {}
tasks_id_seq = 0


def now_utc() -> datetime:
    return datetime.now(timezone.utc)

@app.post("/tasks", response_model=TaskOut, status_code=201)
async def create_task(dto: TaskCreate):
    global tasks_id_seq
    
    tasks_id_seq += 1
    now = now_utc()

    task = {
       "id": tasks_id_seq,
       "title": dto.title,
       "description": dto.description,
       "status": "в процессе",
       "created_at": now,
       "updated_at": now
    }
    
    tasks[task["id"]] = task
    return task

@app.get("/tasks", response_model=list[TaskOut])
async def list_tasks():
    return list(tasks.values())

@app.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(task_id: int):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return task

@app.patch("/tasks/{task_id}", response_model=TaskOut)
async def patch_task(task_id: int, dto: TaskPatch):
    task = tasks.get(task_id)
    if not task:
        return HTTPException(status_code=404, detail="task not found")
    
    patch = dto.model_dump(exclude_unset=True)
    if "title" in patch:
        task["title"] = patch["title"]

    if "description" in patch:
        task["description"] = patch["description"]

    if "status" in patch:
        task["status"] = patch["status"]

    task["update_at"] = now_utc()
    return task

@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int):
    if task_id not in tasks:
        return HTTPException(status_code=404, detail="task not found")
    
    tasks.pop(task_id)
    return None
