import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database path in workspace
DATABASE_URL = "sqlite:///./backend.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TaskRecord(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    goal = Column(String, index=True)
    status = Column(String, default="Pending") # Pending, Planning, Executing, Completed, Failed
    summary = Column(Text, default="")
    steps_executed = Column(Text, default="[]") # JSON list of steps executed
    final_report = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_or_update_task(task_data: dict) -> int:
    """Helper to save or update task records in SQLite."""
    db = SessionLocal()
    try:
        task_id = task_data.get("id")
        if task_id:
            # Update existing task
            task = db.query(TaskRecord).filter(TaskRecord.id == task_id).first()
            if task:
                for key, val in task_data.items():
                    if key != "id":
                        setattr(task, key, val)
                db.commit()
                return task.id
        else:
            # Insert new task
            task = TaskRecord(
                goal=task_data.get("goal"),
                status=task_data.get("status", "Pending"),
                summary=task_data.get("summary", ""),
                steps_executed=task_data.get("steps_executed", "[]"),
                final_report=task_data.get("final_report", "")
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return task.id
    except Exception as e:
        print(f"[Database Error] Could not write to DB: {e}")
        return -1
    finally:
        db.close()
