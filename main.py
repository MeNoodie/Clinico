from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.auth.login import router as login_router
from backend.auth.register import router as register_router
from backend.api.chat import router as chat_router
from backend.api.appointments import router as appointments_router
from backend.database.db import Base, engine
import backend.models.data_models  # Register all ORM models with Base metadata.

app = FastAPI(title="Clinico - Your AI receptionist")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],)

app.include_router(register_router)
app.include_router(login_router)
app.include_router(chat_router)
app.include_router(appointments_router)


@app.on_event("startup")
def initialize_database() -> None:
    """Create new tables and add the user link for existing local databases."""
    from sqlalchemy import inspect, text

    Base.metadata.create_all(bind=engine)
    columns = {column["name"] for column in inspect(engine).get_columns("patients")}
    if "user_id" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE patients ADD COLUMN user_id INTEGER"))

@app.get("/")
def root():
    return {"message": "Welcome to the Clinico. Go to /docs to test!"}


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Clinico"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000)
