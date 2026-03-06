from fastapi import FastAPI

app = FastAPI(
    title="BookVault API",
    description="A RESTful API for book metadata and analytics",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"message": "Welcome to BookVault API"}