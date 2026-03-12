from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.database import get_db
from app.models.models import Book, Review

router = APIRouter()


# ─── GET /authors ─────────────────────────────────────────────────────────────
@router.get("/")
def get_authors(
    search: Optional[str] = Query(None, description="Search by author name"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = (
        db.query(Book.authors, func.count(Book.id).label("book_count"))
        .group_by(Book.authors)
    )

    if search:
        query = query.filter(Book.authors.ilike(f"%{search}%"))

    total = query.count()
    results = query.order_by(func.count(Book.id).desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [
            {"authors": r.authors, "book_count": r.book_count}
            for r in results
        ]
    }


# ─── GET /authors/{name}/books ────────────────────────────────────────────────
@router.get("/{author_name}/books")
def get_author_books(
    author_name: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    books = (
        db.query(Book)
        .filter(Book.authors.ilike(f"%{author_name}%"))
        .offset(offset).limit(limit)
        .all()
    )

    if not books:
        raise HTTPException(status_code=404, detail=f"No books found for author '{author_name}'")

    return {
        "author": author_name,
        "book_count": len(books),
        "books": [
            {
                "id": b.id,
                "title": b.title,
                "average_rating": b.average_rating,
                "ratings_count": b.ratings_count,
                "publication_date": b.publication_date,
                "publisher": b.publisher
            }
            for b in books
        ]
    }


# ─── GET /authors/{name}/stats ────────────────────────────────────────────────
@router.get("/{author_name}/stats")
def get_author_stats(author_name: str, db: Session = Depends(get_db)):
    books = db.query(Book).filter(Book.authors.ilike(f"%{author_name}%")).all()

    if not books:
        raise HTTPException(status_code=404, detail=f"No books found for author '{author_name}'")

    avg_rating = sum(b.average_rating for b in books if b.average_rating) / len(books)
    total_ratings = sum(b.ratings_count for b in books if b.ratings_count)
    total_reviews = sum(b.text_reviews_count for b in books if b.text_reviews_count)

    top_book = max(
        [b for b in books if b.average_rating],
        key=lambda b: b.average_rating,
        default=None
    )

    most_rated_book = max(
        [b for b in books if b.ratings_count],
        key=lambda b: b.ratings_count,
        default=None
    )

    return {
        "author": author_name,
        "total_books": len(books),
        "avg_rating": round(avg_rating, 2),
        "total_ratings_received": total_ratings,
        "total_text_reviews": total_reviews,
        "top_rated_book": {
            "title": top_book.title,
            "average_rating": top_book.average_rating
        } if top_book else None,
        "most_rated_book": {
            "title": most_rated_book.title,
            "ratings_count": most_rated_book.ratings_count
        } if most_rated_book else None
    }