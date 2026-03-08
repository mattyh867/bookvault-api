from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional

from app.database import get_db
from app.models.models import Book, Genre

router = APIRouter()


# ─── GET /books ───────────────────────────────────────────────────────────────
# List all books, with optional search/filter query params
@router.get("/")
def get_books(
    search: Optional[str] = Query(None, description="Search by title or author"),
    genre: Optional[str] = Query(None, description="Filter by genre name"),
    year: Optional[int] = Query(None, description="Filter by year of publication"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    query = db.query(Book)

    # Search by title or author
    if search:
        query = query.filter(
            or_(
                Book.title.ilike(f"%{search}%"),
                Book.author.ilike(f"%{search}%")
            )
        )

    # Filter by genre
    if genre:
        query = query.join(Book.genres).filter(Genre.name.ilike(f"%{genre}%"))

    # Filter by year
    if year:
        query = query.filter(Book.year_of_publication == str(year))

    total = query.count()
    books = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [format_book(b) for b in books]
    }


# ─── GET /books/{id} ──────────────────────────────────────────────────────────
# Get a single book by ID
@router.get("/{book_id}")
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()

    if not book:
        raise HTTPException(status_code=404, detail=f"Book with id {book_id} not found")

    return format_book(book)


# ─── POST /books ──────────────────────────────────────────────────────────────
# Create a new book
@router.post("/", status_code=201)
def create_book(payload: dict, db: Session = Depends(get_db)):
    # Extract genre IDs if provided
    genre_ids = payload.pop("genre_ids", [])

    book = Book(**payload)

    # Link genres
    if genre_ids:
        genres = db.query(Genre).filter(Genre.id.in_(genre_ids)).all()
        if len(genres) != len(genre_ids):
            raise HTTPException(status_code=404, detail="One or more genre IDs not found")
        book.genres = genres

    db.add(book)
    db.commit()
    db.refresh(book)

    return {"message": "Book created successfully", "book": format_book(book)}


# ─── PUT /books/{id} ──────────────────────────────────────────────────────────
# Update an existing book (partial update supported)
@router.put("/{book_id}")
def update_book(book_id: int, payload: dict, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()

    if not book:
        raise HTTPException(status_code=404, detail=f"Book with id {book_id} not found")

    # Update genre links if provided
    genre_ids = payload.pop("genre_ids", None)
    if genre_ids is not None:
        genres = db.query(Genre).filter(Genre.id.in_(genre_ids)).all()
        book.genres = genres

    # Update remaining fields
    for field, value in payload.items():
        if hasattr(book, field):
            setattr(book, field, value)

    db.commit()
    db.refresh(book)

    return {"message": "Book updated successfully", "book": format_book(book)}


# ─── DELETE /books/{id} ───────────────────────────────────────────────────────
# Delete a book by ID
@router.delete("/{book_id}", status_code=200)
def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()

    if not book:
        raise HTTPException(status_code=404, detail=f"Book with id {book_id} not found")

    db.delete(book)
    db.commit()

    return {"message": f"Book '{book.title}' deleted successfully"}


# ─── GET /books/top-rated ─────────────────────────────────────────────────────
# Returns top rated books — useful preview before analytics router is built
@router.get("/top-rated")
def top_rated_books(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    from sqlalchemy import func
    results = (
        db.query(Book, func.avg(Book.reviews.property.mapper.class_.rating).label("avg_rating"))
        .join(Book.reviews)
        .group_by(Book.id)
        .order_by(func.avg(Book.reviews.property.mapper.class_.rating).desc())
        .limit(limit)
        .all()
    )
    return [
        {"title": b.Book.title, "author": b.Book.author, "avg_rating": round(b.avg_rating, 2)}
        for b in results
    ]


# ─── Helper ───────────────────────────────────────────────────────────────────
def format_book(book: Book) -> dict:
    return {
        "id": book.id,
        "bookId": book.bookId,
        "title": book.title,
        "author": book.author,
        "year_of_publication": book.year_of_publication,
        "publisher": book.publisher,
        "imageURL_S": book.imageURL_S,
        "imageURL_M": book.imageURL_M,
        "imageURL_L": book.imageURL_L,
        "genres": [{"id": g.id, "name": g.name} for g in book.genres],
        "review_count": len(book.reviews),
    }