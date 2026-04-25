from fastapi import FastAPI
from app.database import engine
from app.models.calendar import Base
from routes.calendar import router
import threading
from app.utils.scheduler import run_scheduler

app = FastAPI()

app.include_router(router)

# 🔥 start scheduler
threading.Thread(target=run_scheduler, daemon=True).start()

@app.get("/")
def test():
    return {"ok": True}