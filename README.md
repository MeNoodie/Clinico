<h1 align="center">Clinico</h1>

<p align="center">
  <strong>Your care journey, made simpler.</strong><br />
  Manage appointments and medical reports, and get guided support from an AI assistant.
</p>

<p align="center">
  <code>Next.js</code> &nbsp; <code>FastAPI</code> &nbsp; <code>LangGraph</code> &nbsp; <code>SQLAlchemy</code>
</p>

## What you can do

| Feature | Description |
|---|---|
| **Manage appointments** | View upcoming, past, and cancelled visits. Start guided booking, cancellation, rescheduling, and follow-up workflows. |
| **Keep reports together** | Upload PDF and image reports, then preview, download, or delete them from your patient account. |
| **Get guided AI support** | Chat through a multi-step workflow with intent collection, safety checks, department routing, and appointment actions. |
| **Manage your account** | Sign up, log in, view your patient dashboard, and edit your profile. |

The app includes a **Next.js frontend** and a **FastAPI backend**. Patient routes require JWT authentication, and appointment and document operations are scoped to the signed-in patient.

## Project layout

- `backend/agents/` — LangGraph workflow and agent logic.
- `backend/api/` — FastAPI routes for appointments, chat, dashboard, documents, and profile.
- `backend/auth/` — Signup, login, JWT security, and patient dependencies.
- `backend/database/` — SQLAlchemy engine and application database configuration.
- `backend/models/` — SQLAlchemy models.
- `backend/tools/` — Appointment action tools used by the workflow.
- `frontend/` — Next.js patient interface.
- `main.py` — FastAPI application entry point.
- `Dockerfile`, `render.yaml` — Backend container and Render service configuration.

## Data storage

The project currently uses two SQLite databases:

1. The application database (`clinico.db`) stores users, patients, doctors, departments, appointments, uploaded document metadata, and AI assistant session records. Set `SQLITE_DB_PATH` or `DATABASE_URL` to select its location.
2. `clinico_memory.sqlite` stores LangGraph workflow checkpoints, including conversation state.

Uploaded report files are stored separately under `uploads/medical_documents/<patient_id>/` by default. `MEDICAL_DOCUMENTS_DIR` can override that location.

Chat session ownership and the initial workflow context are saved in the application database. With both the application database and checkpoint database on persistent storage, an existing session can resume after a backend restart as long as the client still has its session ID.

The Render configuration stores all persistent application data on its `/data` disk: `/data/clinico.db`, `/data/clinico_memory.sqlite`, and `/data/medical_documents`. The Blueprint uses Render's paid `starter` service plan because persistent disks aren't available on free web services. Keep these paths on the disk for workflow checkpoints and uploaded reports to survive deploys and restarts.

## API overview

All patient routes below require `Authorization: Bearer <access_token>`, except signup and login.

### Authentication and profile

- `POST /auth/signup` — create a patient account.
- `POST /auth/login` — authenticate and receive a JWT.
- `GET /auth/me` — return the signed-in patient's profile.
- `GET /users/{user_id}` — get the current user's profile.
- `PATCH /users/{user_id}` or `PUT /users/{user_id}` — update the current user's name, email, or phone.

### Dashboard and appointments

- `GET /dashboard/stats` — patient document and conversation totals.
- `GET /appointments/history` — list the signed-in patient's appointments.
- `POST /appointments/{appointment_id}/cancel` — start cancellation assistance.
- `POST /appointments/{appointment_id}/reschedule` — start rescheduling assistance.
- `POST /appointments/{appointment_id}/followup` — start follow-up assistance.
- `POST /chat/appointments` — submit a single-shot appointment request.
- `POST /chat/session/start` and `POST /chat/session/reply` — start and continue a guided chat session.

Appointment action endpoints verify ownership and return a session ID and opening message for the chat UI.

### Medical documents

- `POST /documents/upload` — upload a report as multipart form field `file`.
- `GET /documents/recent` — list the patient's recent reports.
- `GET /documents/{document_id}/view` — view a report inline.
- `GET /documents/{document_id}/download` — download a report.
- `DELETE /documents/{document_id}` — delete the report and its stored file.

Document endpoints only return or modify documents belonging to the authenticated patient.

### Service status

- `GET /` — API welcome message.
- `GET /api/health` — health check.
- `GET /docs` — interactive FastAPI documentation while the backend is running.

## Local development

### Requirements

- Python 3.12 or later.
- Node.js and npm (or pnpm).
- A Groq API key for the default model. The `fast` model configuration also requires a Gemini API key.

### Backend

Create a `.env` file from the example and set at least `SECRET_KEY` (or `JWT_SECRET_KEY`) and `GROQ_API_KEY`:

```powershell
Copy-Item .env.example .env
```

Install dependencies and start the API from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --env-file .env
```

The API is available at `http://localhost:8000`.

### Frontend

In another terminal:

```powershell
cd frontend
npm install
$env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
npm run dev
```

Open `http://localhost:3000`. `NEXT_PUBLIC_API_URL` defaults to `http://localhost:8000` when unset.

## Deployment

The repository's `render.yaml` deploys the backend as a Docker web service and mounts a persistent disk at `/data` for the application SQLite database. The frontend is not included in that Render service configuration and needs its own frontend deployment. Set the required model API key and application secrets in the deployment environment. Configure document and LangGraph checkpoint storage on persistent paths if those files need to persist across deploys.

## Notes

- Database tables are created at backend startup with SQLAlchemy `create_all`; this project does not currently define a schema migration workflow.
- Local database files, uploaded reports, and generated frontend build files are excluded from Git by `.gitignore`.
