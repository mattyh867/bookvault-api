from fastapi import FastAPI
from app.database import engine
from app.models.models import Base
from app.routers import books, genres, reviews, authors


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BookVault API",
    description="A RESTful API for book metadata and analytics",
    version="1.0.0"
)

app.include_router(books.router, prefix="/books", tags=["Books"])
app.include_router(genres.router, prefix="/genres", tags=["Genres"])
app.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])
app.include_router(authors.router, prefix="/authors", tags=["Authors"])

@app.get("/")
def root():
    return {"message": "Welcome to BookVault API"}