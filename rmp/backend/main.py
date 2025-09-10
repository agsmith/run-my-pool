
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import models
import database
import routers
from sqlalchemy.orm import Session
import uvicorn
import os

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="RunMyPool API")

# Get CORS origins from environment variable
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routers.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the RunMyPool FastAPI backend!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
