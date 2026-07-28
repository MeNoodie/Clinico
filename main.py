import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import logfire

from backend.auth.login import router as login_router
from backend.auth.register import router as register_router
from backend.api.chat import router as chat_router
from backend.api.appointments import router as appointments_router
from backend.database.db import Base, engine
import backend.models.data_models  # Register all ORM models with Base metadata.

# Initialize Logfire
logfire.configure()

app = FastAPI(title="Clinico - Your AI receptionist")

# Instrument FastAPI with Logfire
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
        logfire.info("Database initialized successfully.")
    except Exception as e:
        logfire.error(f"Failed to initialize database: {e}")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Clinico"}

# Serve frontend static files if they exist (for production deployment)
frontend_dist = Path(__file__).parent / "frontend-react" / "dist"
if frontend_dist.exists() and frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")
    
    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        # Allow API routes to 404 naturally
        if full_path.startswith("api/") or full_path.startswith("auth/") or full_path.startswith("chat/") or full_path.startswith("appointments/") or full_path == "docs" or full_path == "openapi.json":
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not Found")
            
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Frontend build not found."}
else:
    @app.get("/")
    def root():
        return {"message": "Welcome to the Clinico API. Go to /docs to test!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
