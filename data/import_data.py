import pandas as pd
import sys
import os

# Allow running from project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, Base, engine
from app.models.models import Book

# Ensure tables exist (safe to call even if already created)
Base.metadata.create_all(bind=engine)

def clean_int(val):
    try:
        return int(float(str(val).strip()))
    except:
        return None

def clean_float(val):
    try:
        return float(str(val).strip())
    except:
        return None

def run_import(csv_path: str = "data/booksnew.csv", limit: int = None):
    print(f"Loading CSV from {csv_path}...")
    df = pd.read_csv(csv_path, encoding="utf-8", on_bad_lines="skip")
    df.columns = df.columns.str.strip()  # strip any whitespace from column names

    if limit:
        df = df.head(limit)

    print(f"Importing {len(df)} books...")

    db = SessionLocal()
    imported = 0
    skipped = 0

    for _, row in df.iterrows():
        # Skip if title is missing
        if pd.isna(row.get("title")):
            skipped += 1
            continue

        # Avoid duplicates by bookID
        existing = db.query(Book).filter(Book.bookID == str(row.get("bookID", ""))).first()
        if existing:
            skipped += 1
            continue

        book = Book(
            bookID=str(row.get("bookID", "")).strip(),
            title=str(row.get("title", "")).strip(),
            authors=str(row.get("authors", "")).strip(),
            average_rating=clean_float(row.get("average_rating")),
            isbn=str(row.get("isbn", "")).strip(),
            isbn13=str(row.get("isbn13", "")).strip(),
            language_code=str(row.get("language_code", "")).strip(),
            num_pages=clean_int(row.get("  num_pages")),  # note: dataset has leading spaces
            ratings_count=clean_int(row.get("ratings_count")),
            text_reviews_count=clean_int(row.get("text_reviews_count")),
            publication_date=str(row.get("publication_date", "")).strip(),
            publisher=str(row.get("publisher", "")).strip(),
        )

        db.add(book)
        imported += 1

        # Commit in batches of 500 for performance
        if imported % 500 == 0:
            db.commit()
            print(f"  {imported} books imported...")

    db.commit()
    db.close()

    print(f"\nDone. Imported: {imported} | Skipped: {skipped}")


if __name__ == "__main__":
    # Optional: pass a limit as a command line argument for testing
    # e.g. python data/import.py 100
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_import(limit=limit)