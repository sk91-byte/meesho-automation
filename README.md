# Instagram AI Automation & Reselling Management Platform

Production-grade Instagram AI sales assistant and reselling management platform engineered specifically for Meesho resellers.

## Core Features
1. **AI Instagram Direct Message Assistant**: Powered by Groq LLM API with multilingual support (Hindi, English, Hinglish, Devanagari, and Latin script).
2. **6-Layer Anti-Hallucination Architecture**: "AI decides what the customer means, Backend decides what is true." Strictly prevents invented prices, stock, or discounts.
3. **Official Meta Instagram Graph API Integration**: Secure OAuth tokens with AES-256-GCM encryption at rest, HMAC SHA-256 webhook signature verification, and idempotent event handling.
4. **Conversational Order Engine**: State machine collecting customer name, phone, house/building, and road/area/colony with explicit confirmation and immutable price snapshots.
5. **Customer Request Analytics**: Automatic detection and tracking of unavailable colors/sizes requested by customers for market research.
6. **Human Handoff & Control**: Live chat viewer with one-click "Pause AI & Takeover" and "Resume AI" controls for the business owner.
7. **Nightly Business Summaries**: Data-driven executive reports on orders, revenue, expected gross margin, customer requests, and AI validation metrics.

## Tech Stack
- **Backend**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), Groq SDK (`groq`).
- **Frontend**: React, TypeScript, Vite, Tailwind CSS, Lucide Icons.
- **Database**: PostgreSQL / Async SQLite with Alembic migrations.
- **Security**: JWT authentication, bcrypt password hashing, AES-256-GCM encryption, HMAC SHA-256 webhook verification.

## Documentation Links
- [SETUP.md](file:///C:/Users/saksh/.gemini/antigravity/scratch/instagram-reseller-ai/SETUP.md)
- [SECURITY.md](file:///C:/Users/saksh/.gemini/antigravity/scratch/instagram-reseller-ai/SECURITY.md)
- [ARCHITECTURE.md](file:///C:/Users/saksh/.gemini/antigravity/scratch/instagram-reseller-ai/ARCHITECTURE.md)
- [API.md](file:///C:/Users/saksh/.gemini/antigravity/scratch/instagram-reseller-ai/API.md)
- [DATABASE.md](file:///C:/Users/saksh/.gemini/antigravity/scratch/instagram-reseller-ai/DATABASE.md)
