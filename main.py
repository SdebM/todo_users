from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
import asyncio 


app = FastAPI(title="ToDo v1 (in-memory)")

TaskStatus = Literal["queued", "done", "cancelled"]

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

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

class Store:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._tasks: dict[int, dict] = {}
        self._task_id_seq = 0

    async def create_task(self, title: str, description: str | None) -> dict:
        async with self._lock:
            self._task_id_seq += 1
            now = now_utc()

            task = {
                "id": self._task_id_seq,
                "title": title,
                "description": description,
                "status": "queued",
                "created_at": now,
                "updated_at": now,
            }
                
            self._tasks[task["id"]] = task
            return task
    
    async def list_tasks(self) -> list[dict]:
        async with self._lock:
            return list(self._tasks.values())
        
    async def get_task(self, task_id: int) -> dict | None:
        async with self._lock:
            return self._tasks.get(task_id)
        
    async def patch_task(self, task_id: int, patch: dict) -> dict:
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise KeyError("task not found")
             
            for k in ("title", "description", "status"):
                if k in patch:
                    task[k] = patch[k]

            task["updated_at"] = now_utc()
            return task
         
    async def delete_task(self, task_id: int) -> None:
        async with self._lock:
            if task_id not in self._tasks:
                raise KeyError("task not found")
            self._tasks.pop(task_id)

    async def cancel_task(self, task_id: int) -> dict:
        return await self.patch_task(task_id, {"status": "cancelled"})
    
store = Store()

@app.post("/tasks", response_model=TaskOut, status_code=201)
async def create_task(dto: TaskCreate):
    return await store.create_task(dto.title, dto.description)

@app.get("/tasks", response_model=list[TaskOut])
async def list_tasks():
    return await store.list_tasks()

@app.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(task_id: int):
    task = await store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return task

@app.patch("/tasks/{task_id}", response_model=TaskOut)
async def patch_task(task_id: int, dto: TaskPatch):
    try:
        patch = dto.model_dump(exclude_unset=True)
        return await store.patch_task(task_id, patch)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found")
    
    
@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int):
    try:
        await store.delete_task(task_id)
        return None
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found")
    

@app.post("/tasks/{task_id}/cancel", response_model=TaskOut)
async def cancel_task(task_id: int):
    try:
        return await store.cancel_task(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found")
