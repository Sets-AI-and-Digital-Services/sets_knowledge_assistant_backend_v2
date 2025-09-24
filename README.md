# SETS Chatbot v2 (FastAPI + MongoDB)

This is the refactored backend for **SETS-Chatbot**, built with **FastAPI** and **MongoDB**, supporting:
- Retrieval-Augmented Generation (RAG) chatbot endpoints (from v1)
- JWT Authentication
- Role-based access control (**only admins can create users**)
- Compatibility with the **same database and collections** as the previous project

---

## 🚀 Features
- Upload files, process them, and query using RAG (as in v1)
- Session and feedback storage in MongoDB
- **Authentication with JWT** (`/login`)
- **Admin-only Create User** endpoint (`/users`)
- Configurable via `.env`

---

## 📂 Project Structure
sets_chatbot_v2/
│── app/
│ ├── api/v1/ # Routers (auth, users, etc.)
│ ├── core/ # Config, DB connection, security
│ ├── domain/ # Pydantic models
│ ├── services/ # Business logic (auth, users, rag)
│ └── main.py # FastAPI entrypoint
│── scripts/ # Utility scripts (seed_admin, test_db)
│── requirements.txt
│── README.md
│── .env.example


