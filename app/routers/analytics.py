from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.database import get_db
from app.models.models import Book, Genre, Review, book_genre

router = APIRouter()


# ─── GET /analytics/genre-trends ─────────────────────────────────────────────
# Most popular genres ranked by average rating and book count
@router.get("/genre-trends")
def genre_trends(
    min_books: int = Query(5, description="Minimum number of books a genre must have"),
    db: Session = Depends(get_db)
):
    results = (
        db.query(
            Genre.name,
            func.avg(Review.rating).label("avg_rating"),
            func.count(Book.id.distinct()).label("book_count"),
            func.count(Review.id).label("review_count")
        )
        .join(book_genre, book_genre.c.genre_id == Genre.id)
        .join(Book, Book.id == book_genre.c.book_id)
        .outerjoin(Review, Review.book_id == Book.id)
        .group_by(Genre.name)
        .having(func.count(Book.id.distinct()) >= min_books)
        .order_by(func.avg(Review.rating).desc())
        .all()
    )

    return {
        "total_genres": len(results),
        "genres": [
            {
                "genre": r.name,
                "avg_rating": round(r.avg_rating, 2) if r.avg_rating else None,
                "book_count": r.book_count,
                "review_count": r.review_count
            }
            for r in results
        ]
    }


# ─── GET /analytics/rating-distribution ──────────────────────────────────────
# Histogram of how ratings are spread across the whole dataset
@router.get("/rating-distribution")
def rating_distribution(db: Session = Depends(get_db)):
    results = (
        db.query(
            Review.rating.label("rating"),
            func.count(Review.id).label("count")
        )
        .group_by(Review.rating)
        .order_by(Review.rating)
        .all()
    )

    total_reviews = sum(r.count for r in results)

    return {
        "total_reviews": total_reviews,
        "distribution": [
            {
                "rating": r.rating,
                "count": r.count,
                "percentage": round((r.count / total_reviews) * 100, 1) if total_reviews else 0
            }
            for r in results
        ]
    }


# ─── GET /analytics/top-publishers ───────────────────────────────────────────
# Publishers ranked by average rating of their books
@router.get("/top-publishers")
def top_publishers(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    results = (
        db.query(
            Book.publisher,
            func.avg(Review.rating).label("avg_rating"),
            func.count(Book.id.distinct()).label("book_count"),
            func.count(Review.id).label("review_count")
        )
        .join(Review, Review.book_id == Book.id)
        .filter(Book.publisher != None)
        .group_by(Book.publisher)
        .having(func.count(Review.id) >= 10)  # only publishers with enough reviews
        .order_by(func.avg(Review.rating).desc())
        .limit(limit)
        .all()
    )

    return {
        "publishers": [
            {
                "publisher": r.publisher,
                "avg_rating": round(r.avg_rating, 2),
                "book_count": r.book_count,
                "review_count": r.review_count
            }
            for r in results
        ]
    }


# ─── GET /analytics/publication-trends ───────────────────────────────────────
# Average rating and book count broken down by publication year
@router.get("/publication-trends")
def publication_trends(
    start_year: Optional[int] = Query(None, description="Start year filter"),
    end_year: Optional[int] = Query(None, description="End year filter"),
    db: Session = Depends(get_db)
):
    query = (
        db.query(
            Book.year_of_publication.label("year"),
            func.avg(Review.rating).label("avg_rating"),
            func.count(Book.id.distinct()).label("book_count")
        )
        .join(Review, Review.book_id == Book.id)
        .filter(Book.year_of_publication != None)
        .filter(Book.year_of_publication != "0")
        .group_by(Book.year_of_publication)
        .order_by(Book.year_of_publication)
    )

    if start_year:
        query = query.filter(Book.year_of_publication >= str(start_year))
    if end_year:
        query = query.filter(Book.year_of_publication <= str(end_year))

    results = query.all()

    return {
        "total_years": len(results),
        "trends": [
            {
                "year": r.year,
                "avg_rating": round(r.avg_rating, 2) if r.avg_rating else None,
                "book_count": r.book_count
            }
            for r in results
        ]
    }


# ─── GET /analytics/most-reviewed ────────────────────────────────────────────
# Books with the most reviews (most talked about)
@router.get("/most-reviewed")
def most_reviewed(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    results = (
        db.query(
            Book,
            func.count(Review.id).label("review_count"),
            func.avg(Review.rating).label("avg_rating")
        )
        .join(Review, Review.book_id == Book.id)
        .group_by(Book.id)
        .order_by(func.count(Review.id).desc())
        .limit(limit)
        .all()
    )

    return {
        "books": [
            {
                "id": r.Book.id,
                "title": r.Book.title,
                "author": r.Book.author,
                "review_count": r.review_count,
                "avg_rating": round(r.avg_rating, 2) if r.avg_rating else None
            }
            for r in results
        ]
    }


# ─── GET /analytics/summary ───────────────────────────────────────────────────
# High level dataset summary — good for an API homepage/dashboard
@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    total_books = db.query(func.count(Book.id)).scalar()
    total_reviews = db.query(func.count(Review.id)).scalar()
    total_genres = db.query(func.count(Genre.id)).scalar()
    avg_rating = db.query(func.avg(Review.rating)).scalar()

    top_book = (
        db.query(Book, func.avg(Review.rating).label("avg"))
        .join(Review)
        .group_by(Book.id)
        .having(func.count(Review.id) >= 5)
        .order_by(func.avg(Review.rating).desc())
        .first()
    )

    return {
        "total_books": total_books,
        "total_reviews": total_reviews,
        "total_genres": total_genres,
        "overall_avg_rating": round(avg_rating, 2) if avg_rating else None,
        "top_rated_book": {
            "title": top_book.Book.title,
            "author": top_book.Book.author,
            "avg_rating": round(top_book.avg, 2)
        } if top_book else None
    }