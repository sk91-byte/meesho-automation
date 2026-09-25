# Production Deployment Guide: Render & PostgreSQL

This document provides step-by-step instructions for deploying the **Instagram AI Automation & Reselling Platform** to Render (Backend Web Service + Render PostgreSQL Database) with rapid webhook buffer protection to prevent cold-start timeouts.

---

## Architecture Overview

```text
                               Meta Instagram Platform
                                          │
                                          ▼ (POST Webhook)
                             ┌──────────────────────────┐
                             │    Render Web Service    │
                             │  (FastAPI Backend API)   │
                             └────────────┬─────────────┘
                                          │
                  ┌───────────────────────┼───────────────────────┐
                  ▼                       ▼                       ▼
       ┌────────────────────┐   ┌───────────────────┐   ┌────────────────────┐
       │ Render PostgreSQL  │   │     Groq AI       │   │   Cloudflare R2    │
       │     Database       │   │   (LLM Engine)    │   │ (Product Images)   │
       └────────────────────┘   └───────────────────┘   └────────────────────┘
```

---

## 1. Webhook Cold-Start & Waiting Queue Safety (§46 & §47)

Meta Instagram Webhooks require a rapid HTTP 200 OK acknowledgment within 5 seconds. On free or sleeping Render web services, a cold start or long LLM turn could cause Meta to timeout and retry.

### How We Solved It:
1. **Rapid ACK (< 200ms)**: The `/api/v1/webhooks/instagram` endpoint verifies HMAC signatures and immediately returns `HTTP 200 OK {"status": "received"}`.
2. **Asynchronous Background Task Queue**: Payload processing (Groq AI calls, product lookup, order draft updates) is pushed to a background task worker (`async_process_webhook_payload`).
3. **Grounded Delivery**: The final response is delivered to the customer via Meta Direct Message once processing completes, with zero risk of dropped webhook turns.

---

## 2. Setting Up Render PostgreSQL Database

1. Go to [Render Dashboard](https://dashboard.render.com/) and click **New +** $\rightarrow$ **PostgreSQL**.
2. Name: `instagram-reseller-db`
3. Region: Select closest region (e.g. `Singapore` or `Frankfurt`).
4. Database: `instagram_reseller_db`
5. User: `postgres`
6. Click **Create Database**.
7. Copy the **Internal Database URL** (e.g. `postgresql://postgres:...@dpg-xxx-a:5432/instagram_reseller_db`).

---

## 3. Deploying FastAPI Backend Web Service on Render

1. Click **New +** $\rightarrow$ **Web Service**.
2. Connect your Git repository.
3. Configuration Settings:
   - **Name**: `instagram-reseller-api`
   - **Environment**: `Python 3`
   - **Region**: Same region as PostgreSQL
   - **Branch**: `main`
   - **Root Directory**: `backend` (or root if using root structure)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 4. Configure Environment Variables in Render

In your Render Web Service $\rightarrow$ **Environment** tab, add:

| Environment Variable | Value / Description |
| :--- | :--- |
| `DATABASE_URL` | Render PostgreSQL URL (change prefix from `postgresql://` to `postgresql+asyncpg://`) |
| `SECRET_KEY` | 32-byte secret for JWT auth |
| `ENCRYPTION_KEY` | 32-byte hex key for AES-256 GCM token encryption |
| `GROQ_API_KEY` | Groq API key (`gsk_...`) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` |
| `INSTAGRAM_APP_ID` | Meta App ID |
| `INSTAGRAM_APP_SECRET` | Meta App Secret |
| `INSTAGRAM_VERIFY_TOKEN` | Custom string for Meta Webhook verification challenge |
| `ENVIRONMENT` | `production` |
| `LOG_LEVEL` | `INFO` |

---

## 5. First-Time Database Seeding on Render

Once deployed, run the seed script via Render Shell or SSH:
```bash
python backend/init_db.py
```
This creates all PostgreSQL tables and seeds your default owner user (`owner@meesho.store`).

---

## 6. Configuring Meta Instagram Webhooks

1. Go to [Meta Developers Console](https://developers.facebook.com/).
2. Navigate to **Instagram Graph API** $\rightarrow$ **Webhooks**.
3. Callback URL: `https://your-render-app.onrender.com/api/v1/webhooks/instagram`
4. Verify Token: Enter your `INSTAGRAM_VERIFY_TOKEN`.
5. Subscribe to `messages` and `messaging_postbacks`.
