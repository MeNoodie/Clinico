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

# Copy the backend code
COPY backend/ ./backend/
COPY main.py .

# Ensure the persistent data directory exists
RUN mkdir -p /data
ENV SQLITE_DB_PATH=/data/clinico.db

# Expose port and run Uvicorn
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
