from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional

from app.database import get_db
from app.models.models import Book, Review
from app.auth import verify_api_key

router = APIRouter()


# ─── GET /books ───────────────────────────────────────────────────────────────
@router.get("/")
def get_books(
    search: Optional[str] = Query(None, description="Search by title or author"),
    publisher: Optional[str] = Query(None, description="Filter by publisher"),
    language: Optional[str] = Query(None, description="Filter by language code e.g. 'eng'"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum average rating"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(Book)

    if search:
        query = query.filter(
            or_(
                Book.title.ilike(f"%{search}%"),
                Book.authors.ilike(f"%{search}%")
            )
        )
    if publisher:
        query = query.filter(Book.publisher.ilike(f"%{publisher}%"))
    if language:
        query = query.filter(Book.language_code == language)
    if min_rating:
        query = query.filter(Book.average_rating >= min_rating)

    total = query.count()
    books = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [format_book(b) for b in books]
    }


# ─── GET /books/top-rated ─────────────────────────────────────────────────────
@router.get("/top-rated")
def top_rated_books(
    limit: int = Query(10, ge=1, le=50),
    min_ratings_count: int = Query(100, description="Minimum number of ratings for a book to qualify"),
    db: Session = Depends(get_db)
):
    results = (
        db.query(Book)
        .filter(Book.average_rating != None)
        .filter(Book.ratings_count >= min_ratings_count)
        .order_by(Book.average_rating.desc())
        .limit(limit)
        .all()
    )

    return {
        "results": [
            {
                "id": b.id,
                "title": b.title,
                "authors": b.authors,
                "average_rating": b.average_rating,
                "ratings_count": b.ratings_count,
                "publisher": b.publisher,
            }
            for b in results
        ]
    }


# ─── GET /books/recommendations ───────────────────────────────────────────────
@router.get("/recommendations")
def get_recommendations(
    authors: Optional[str] = Query(None, description="Filter by author name"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    min_rating: float = Query(4.0, ge=0, le=5, description="Minimum average rating"),
    min_pages: Optional[int] = Query(None, description="Minimum number of pages"),
    max_pages: Optional[int] = Query(None, description="Maximum number of pages"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    query = (
        db.query(Book)
        .filter(Book.average_rating >= min_rating)
        .filter(Book.ratings_count >= 50)  # filter out books with very few ratings
        .order_by(Book.average_rating.desc())
    )

    if authors:
        query = query.filter(Book.authors.ilike(f"%{authors}%"))
    if language:
        query = query.filter(Book.language_code == language)
    if min_pages:
        query = query.filter(Book.num_pages >= min_pages)
    if max_pages:
        query = query.filter(Book.num_pages <= max_pages)

    results = query.limit(limit).all()

    if not results:
        raise HTTPException(status_code=404, detail="No recommendations found for the given filters")

    return {
        "filters": {
            "authors": authors,
            "language": language,
            "min_rating": min_rating,
            "min_pages": min_pages,
            "max_pages": max_pages
        },
        "count": len(results),
        "recommendations": [format_book(b) for b in results]
    }


# ─── GET /books/{id} ──────────────────────────────────────────────────────────
@router.get("/{book_id}")
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail=f"Book with id {book_id} not found")
    return format_book(book)


# ─── POST /books ──────────────────────────────────────────────────────────────
@router.post("/", status_code=201, dependencies=[Depends(verify_api_key)])
def create_book(payload: dict, db: Session = Depends(get_db)):
    book = Book(**payload)
    db.add(book)
    db.commit()
    db.refresh(book)
    return {"message": "Book created successfully", "book": format_book(book)}


# ─── PUT /books/{id} ──────────────────────────────────────────────────────────
@router.put("/{book_id}", dependencies=[Depends(verify_api_key)])
def update_book(book_id: int, payload: dict, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail=f"Book with id {book_id} not found")

    for field, value in payload.items():
        if hasattr(book, field):
            setattr(book, field, value)

    db.commit()
    db.refresh(book)
    return {"message": "Book updated successfully", "book": format_book(book)}


# ─── DELETE /books/{id} ───────────────────────────────────────────────────────
@router.delete("/{book_id}", dependencies=[Depends(verify_api_key)])
def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail=f"Book with id {book_id} not found")

    db.delete(book)
    db.commit()
    return {"message": f"Book '{book.title}' deleted successfully"}


# ─── Helper ───────────────────────────────────────────────────────────────────
def format_book(book: Book) -> dict:
    return {
        "id": book.id,
        "bookID": book.bookID,
        "title": book.title,
        "authors": book.authors,
        "average_rating": book.average_rating,
        "isbn": book.isbn,
        "isbn13": book.isbn13,
        "language_code": book.language_code,
        "num_pages": book.num_pages,
        "ratings_count": book.ratings_count,
        "text_reviews_count": book.text_reviews_count,
        "publication_date": book.publication_date,
        "publisher": book.publisher,
        "user_review_count": len(book.reviews),
    }