# -----------------------------------
# Build the FastAPI Backend
# -----------------------------------
FROM python:3.12-slim

# Install uv for fast dependency management
RUN pip install uv

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN uv pip install --system --no-cache-dir -r requirements.txt

# The build context is the backend directory in Render.
# Keep the package layout expected by imports such as `backend.api`.
COPY main.py ./backend/main.py
COPY agents/ ./backend/agents/
COPY api/ ./backend/api/
COPY auth/ ./backend/auth/
COPY config/ ./backend/config/
COPY database/ ./backend/database/
COPY LLM/ ./backend/LLM/
COPY models/ ./backend/models/
COPY prompts/ ./backend/prompts/
COPY session/ ./backend/session/
COPY structured/ ./backend/structured/
COPY tools/ ./backend/tools/

# Ensure the persistent data directory exists
RUN mkdir -p /data
ENV SQLITE_DB_PATH=/data/clinico.db
ENV LANGGRAPH_CHECKPOINT_DB_PATH=/data/clinico_memory.sqlite

# Expose port and run Uvicorn
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
