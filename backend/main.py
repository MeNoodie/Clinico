import os
# Reload trigger: query_rewriter_node added
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logfire

from backend.auth.login import router as login_router
from backend.auth.register import router as register_router
from backend.api.chat import router as chat_router
from backend.api.appointments import router as appointments_router
from backend.api.profile import router as profile_router
from backend.api.docs_upload import router as documents_router
from backend.database.db import Base, engine
from backend.api.dashboard import router as dashboard_router
import backend.models.data_models  # Register all ORM models with Base metadata.

app = FastAPI(title="Clinico - Your AI receptionist")

# Enable Logfire only when a production token is configured.
if os.getenv("LOGFIRE_TOKEN"):
    logfire.configure()
    logfire.instrument_fastapi(app)

app.add_middleware(
    CORSMiddleware,
    # In production, this should be specific origins or '*' for public API
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(register_router)
app.include_router(login_router)
app.include_router(chat_router)
app.include_router(appointments_router)
app.include_router(profile_router)
app.include_router(documents_router)
app.include_router(dashboard_router)

@app.on_event("startup")
def initialize_database() -> None:
    """Create new tables and add the user link for existing local databases."""
    from sqlalchemy import inspect, text

    try:
        Base.metadata.create_all(bind=engine)
        columns = {column["name"] for column in inspect(engine).get_columns("patients")}
        if "user_id" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE patients ADD COLUMN user_id INTEGER"))
        conversation_columns = {
            column["name"]
            for column in inspect(engine).get_columns("patient_conversations")
        }
        with engine.begin() as connection:
            if "intent" not in conversation_columns:
                connection.execute(text(
                    "ALTER TABLE patient_conversations ADD COLUMN intent VARCHAR(50)"
                ))
            if "appointment_id" not in conversation_columns:
                connection.execute(text(
                    "ALTER TABLE patient_conversations ADD COLUMN appointment_id INTEGER"
                ))
        logfire.info("Database initialized successfully.")
    except Exception as e:
        logfire.error(f"Failed to initialize database: {e}")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Clinico"}

@app.get("/")
def root():
    return {"message": "Welcome to the Clinico API. Go to /docs to test!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
