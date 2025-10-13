# app/main.py
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env", override=True)  # <-- ensure .env is loaded very early

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router as api_router
import os
import uvicorn

app = FastAPI(title="SETS Chatbot", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount once; the /v1 prefix already exists in app/api/__init__.py
app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "SETS Chatbot API is running"}

if __name__ == "__main__":
    port = int(os.getenv("APIS_PORT", "8002"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, workers=4)