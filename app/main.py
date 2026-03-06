from fastapi import FastAPI
from app.database import engine
from app.models.models import Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BookVault API",
    description="A RESTful API for book metadata and analytics",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"message": "Welcome to BookVault API"}