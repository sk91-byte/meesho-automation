# Setup & Installation Guide

## Quick Start

### 1. Environment Configuration
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```
Fill in:
- `SECRET_KEY`: Secret string for JWT tokens.
- `ENCRYPTION_KEY`: 32-byte hex key for AES-256 GCM token encryption.
- `GROQ_API_KEY`: Groq API key (`gsk_...`).
- `INSTAGRAM_APP_SECRET` & `INSTAGRAM_VERIFY_TOKEN`: Meta Developer App credentials.

### 2. Backend Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Seed initial database owner (owner@meesho.store / Owner123!)
python backend/init_db.py

# Run FastAPI backend server
uvicorn backend.app.main:app --reload --port 8000
```

### 3. Running Automated Tests
```bash
python -m pytest
```

### 4. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open your browser at `http://localhost:3000`.
