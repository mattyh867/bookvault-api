from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.database import get_db
from app.models.models import Book, Review

router = APIRouter()


# ─── GET /analytics/summary ───────────────────────────────────────────────────
@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    total_books = db.query(func.count(Book.id)).scalar()
    total_user_reviews = db.query(func.count(Review.id)).scalar()
    avg_rating = db.query(func.avg(Book.average_rating)).scalar()
    total_ratings = db.query(func.sum(Book.ratings_count)).scalar()

    top_book = (
        db.query(Book)
        .filter(Book.average_rating != None)
        .filter(Book.ratings_count >= 100)
        .order_by(Book.average_rating.desc())
        .first()
    )

    return {
        "total_books": total_books,
        "total_user_reviews": total_user_reviews,
        "total_goodreads_ratings": total_ratings,
        "overall_avg_rating": round(avg_rating, 2) if avg_rating else None,
        "top_rated_book": {
            "title": top_book.title,
            "authors": top_book.authors,
            "average_rating": top_book.average_rating,
            "ratings_count": top_book.ratings_count
        } if top_book else None
    }


# ─── GET /analytics/rating-distribution ──────────────────────────────────────
@router.get("/rating-distribution")
def rating_distribution(db: Session = Depends(get_db)):
    # Bucket ratings into 0.5 increments
    results = (
        db.query(
            (func.round(Book.average_rating * 2) / 2).label("bucket"),
            func.count(Book.id).label("count")
        )
        .filter(Book.average_rating != None)
        .group_by("bucket")
        .order_by("bucket")
        .all()
    )

    total = sum(r.count for r in results)

    return {
        "total_books": total,
        "distribution": [
            {
                "rating_bucket": r.bucket,
                "count": r.count,
                "percentage": round((r.count / total) * 100, 1) if total else 0
            }
            for r in results
        ]
    }


# ─── GET /analytics/top-publishers ───────────────────────────────────────────
@router.get("/top-publishers")
def top_publishers(
    limit: int = Query(10, ge=1, le=50),
    min_books: int = Query(5, description="Minimum books published to qualify"),
    min_ratings: int = Query(100, description="Minimum total ratings across all publisher books to qualify"),
    db: Session = Depends(get_db)
):
    results = (
        db.query(
            Book.publisher,
            func.avg(Book.average_rating).label("avg_rating"),
            func.count(Book.id).label("book_count"),
            func.sum(Book.ratings_count).label("total_ratings")
        )
        .filter(Book.publisher != None)
        .filter(Book.publisher != "")
        .group_by(Book.publisher)
        .having(func.count(Book.id) >= min_books)
        .having(func.sum(Book.ratings_count) >= min_ratings)
        .order_by(func.avg(Book.average_rating).desc())
        .limit(limit)
        .all()
    )

    return {
        "publishers": [
            {
                "publisher": r.publisher,
                "avg_rating": round(r.avg_rating, 2),
                "book_count": r.book_count,
                "total_ratings": r.total_ratings
            }
            for r in results
        ]
    }


# ─── GET /analytics/publication-trends ───────────────────────────────────────
@router.get("/publication-trends")
def publication_trends(
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    # Extract year from publication_date string (format: M/D/YYYY)
    results = (
        db.query(
            func.substr(Book.publication_date, -4).label("year"),
            func.avg(Book.average_rating).label("avg_rating"),
            func.count(Book.id).label("book_count"),
            func.sum(Book.ratings_count).label("total_ratings")
        )
        .filter(Book.publication_date != None)
        .filter(Book.publication_date != "")
        .group_by("year")
        .order_by("year")
        .all()
    )

    # Filter by year range if provided
    if start_year or end_year:
        filtered = []
        for r in results:
            try:
                y = int(r.year)
                if start_year and y < start_year:
                    continue
                if end_year and y > end_year:
                    continue
                filtered.append(r)
            except:
                continue
        results = filtered

    return {
        "total_years": len(results),
        "trends": [
            {
                "year": r.year,
                "avg_rating": round(r.avg_rating, 2) if r.avg_rating else None,
                "book_count": r.book_count,
                "total_ratings": r.total_ratings
            }
            for r in results
        ]
    }


# ─── GET /analytics/most-rated ────────────────────────────────────────────────
@router.get("/most-rated")
def most_rated(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    results = (
        db.query(Book)
        .filter(Book.ratings_count != None)
        .order_by(Book.ratings_count.desc())
        .limit(limit)
        .all()
    )

    return {
        "books": [
            {
                "id": b.id,
                "title": b.title,
                "authors": b.authors,
                "ratings_count": b.ratings_count,
                "average_rating": b.average_rating,
                "publisher": b.publisher
            }
            for b in results
        ]
    }


# ─── GET /analytics/language-breakdown ───────────────────────────────────────
@router.get("/language-breakdown")
def language_breakdown(db: Session = Depends(get_db)):
    results = (
        db.query(
            Book.language_code,
            func.count(Book.id).label("book_count"),
            func.avg(Book.average_rating).label("avg_rating")
        )
        .filter(Book.language_code != None)
        .filter(Book.language_code != "")
        .group_by(Book.language_code)
        .order_by(func.count(Book.id).desc())
        .all()
    )

    total = sum(r.book_count for r in results)

    return {
        "total_languages": len(results),
        "languages": [
            {
                "language_code": r.language_code,
                "book_count": r.book_count,
                "percentage": round((r.book_count / total) * 100, 1) if total else 0,
                "avg_rating": round(r.avg_rating, 2) if r.avg_rating else None
            }
            for r in results
        ]
    }