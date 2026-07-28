# -----------------------------------
# Stage 1: Build the React Frontend
# -----------------------------------
FROM node:20-alpine as frontend-builder

WORKDIR /app/frontend
COPY frontend-react/package.json frontend-react/package-lock.json* ./
RUN npm install

COPY frontend-react/ ./
RUN npm run build

# -----------------------------------
# Stage 2: Build the FastAPI Backend
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

# Copy built frontend assets to where main.py expects them
COPY --from=frontend-builder /app/frontend/dist ./frontend-react/dist

# Ensure the persistent data directory exists
RUN mkdir -p /data
ENV SQLITE_DB_PATH=/data/clinico.db

# Expose port and run Uvicorn
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
