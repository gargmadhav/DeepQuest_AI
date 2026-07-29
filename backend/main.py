import os
import json
import asyncio
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from backend.database import get_db, TaskRecord, save_or_update_task
from agent.orchestrator import AgentOrchestrator

app = FastAPI(title="Hermes Autonomous AI Research Assistant API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to React frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Orchestrator
orchestrator = AgentOrchestrator()

# Serve static frontend files
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("backend/static/index.html")

@app.get("/history")
def get_history(db: Session = Depends(get_db)):
    """Fetch past tasks ordered by creation date."""
    tasks = db.query(TaskRecord).order_by(TaskRecord.created_at.desc()).all()
    result = []
    for t in tasks:
        try:
            steps = json.loads(t.steps_executed)
        except Exception:
            steps = []
        result.append({
            "id": t.id,
            "goal": t.goal,
            "status": t.status,
            "summary": t.summary,
            "steps_executed": steps,
            "final_report": t.final_report,
            "created_at": t.created_at.isoformat() if t.created_at else None
        })
    return result

@app.get("/report/{id}")
def get_report(id: int, db: Session = Depends(get_db)):
    """Fetch specific report details."""
    task = db.query(TaskRecord).filter(TaskRecord.id == id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task or report not found")
    
    try:
        steps = json.loads(task.steps_executed)
    except Exception:
        steps = []
        
    return {
        "id": task.id,
        "goal": task.goal,
        "status": task.status,
        "summary": task.summary,
        "steps_executed": steps,
        "final_report": task.final_report,
        "created_at": task.created_at.isoformat() if task.created_at else None
    }

@app.post("/archive/{id}")
def archive_task(id: int, db: Session = Depends(get_db)):
    """Archive a task chat."""
    task = db.query(TaskRecord).filter(TaskRecord.id == id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = "Archived"
    db.commit()
    return {"message": "Task archived successfully", "id": id}

@app.delete("/report/{id}")
def delete_report(id: int, db: Session = Depends(get_db)):
    """Delete a report/task record from database."""
    task = db.query(TaskRecord).filter(TaskRecord.id == id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task or report not found")
    db.delete(task)
    db.commit()
    return {"message": "Report deleted successfully", "id": id}

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WebSocket] Client connected.")
    
    try:
        while True:
            # Receive message from user
            data_str = await websocket.receive_text()
            data = json.loads(data_str)
            goal = data.get("goal", "")
            
            if not goal:
                await websocket.send_json({"type": "error", "message": "Goal cannot be empty."})
                continue
                
            print(f"[WebSocket] Received task: '{goal}'")
            
            # Setup thread-safe callback to stream logs asynchronously
            async def log_callback(msg: str):
                try:
                    await websocket.send_json({
                        "type": "log",
                        "message": msg
                    })
                except Exception as e:
                    print(f"[WS Send Log Error] {e}")
            
            # Setup callback to update DB asynchronously
            async def db_callback(task_data: dict) -> int:
                # Save status update in db
                task_id = save_or_update_task(task_data)
                
                # Prepare payload
                status_payload = {
                    "type": "status",
                    "status": task_data.get("status", "Executing"),
                    "summary": task_data.get("summary", ""),
                    "task_id": task_id
                }
                
                # Include steps if present
                if "steps_executed" in task_data:
                    try:
                        status_payload["steps"] = json.loads(task_data["steps_executed"])
                    except Exception:
                        pass
                        
                # Notify frontend about state updates
                try:
                    await websocket.send_json(status_payload)
                except Exception as e:
                    print(f"[WS Send Status Error] {e}")
                return task_id

            # Start orchestrator execution in a non-blocking task
            try:
                result = await orchestrator.run(
                    goal=goal,
                    db_session_callback=db_callback,
                    log_callback=log_callback
                )
                
                # Send the final structured payload
                await websocket.send_json({
                    "type": "result",
                    "payload": result
                })
            except Exception as agent_error:
                print(f"[WebSocket Error] Agent run failed: {agent_error}")
                # Stream the error details
                await websocket.send_json({
                    "type": "error",
                    "message": f"Agent execution failed: {str(agent_error)}"
                })
                
    except WebSocketDisconnect:
        print("[WebSocket] Client disconnected.")
    except Exception as e:
        print(f"[WebSocket Connection Closed] Error: {e}")
