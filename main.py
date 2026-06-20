import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env on startup
load_dotenv()

# Import routers and db helpers
from routes import classify, complaints, analytics, assistant
from db import init_db

app = FastAPI(title="CityPulse AI Backend", description="Urban Grievance Intelligence API")

# Initialize database on startup
init_db()

# Setup CORS
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://citypulse-ai.vercel.app",
    "https://citypulse-ai-git-main.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(classify.router, prefix="/classify", tags=["classification"])
app.include_router(complaints.router, prefix="/complaints", tags=["complaints"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(assistant.router, prefix="/assistant", tags=["assistant"])

@app.get("/")
def health_check():
    return {"status": "ok", "service": "CityPulse AI API"}
