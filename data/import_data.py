import pandas as pd
from app.database import SessionLocal, engine, Base
from app.models.models import Book, Genre, book_genre

Base.metadata.create_all(bind=engine)

df = pd.read_csv("data/books.csv", encoding="latin-1", on_bad_lines='skip', sep=";")
db = SessionLocal()

for _, row in df.iterrows():
    book = Book(
        id=row["ISBN"],
        title=row["Book-Title"],
        author=row["Book-Author"],
        year_of_publication=str(row["Year-Of-Publication"]),
        publisher=row["Publisher"],
        imageURL_S=row["Image-URL-S"],
        imageURL_M=row["Image-URL-M"],
        imageURL_L=row["Image-URL-L"],
    )
    db.add(book)

db.commit()
db.close()
print("Import complete")