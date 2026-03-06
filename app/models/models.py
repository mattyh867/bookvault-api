from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

user_book_association = Table(
    "user_book_association", Base.metadata,
    Column("user_id", Integer, ForeignKey("user.id")),
    Column("book_id", Integer, ForeignKey("book.id"))
)

book_genre = Table(
    "book_genre", Base.metadata,
    Column("book_id", Integer, ForeignKey("book.id"), primary_key=True),
    Column("genre_id", Integer, ForeignKey("genre.id"), primary_key=True),
)

class Genre(Base):
    __tablename__ = "genre"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    books = relationship("Book", secondary=book_genre, back_populates="genres")

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), index=True, nullable=False)
    password = Column(String(100), nullable=False)
    books = relationship("Book", secondary=user_book_association, back_populates="users")
    reviews = relationship("Review", back_populates="user")

class Book(Base):
    __tablename__ = "book"
    id = Column(String(20), primary_key=True)
    bookId = Column(String(100), index=True)
    title = Column(String(500), index=True)
    author = Column(String(200))
    year_of_publication = Column(String(100))
    publisher = Column(String(100))
    imageURL_S = Column(String(200))
    imageURL_M = Column(String(200))
    imageURL_L = Column(String(200))
    users = relationship("User", secondary=user_book_association, back_populates="books")
    reviews = relationship("Review", back_populates="book", cascade="all, delete-orphan")
    genres = relationship("Genre", secondary=book_genre, back_populates="books")  # ADD

class Review(Base):
    __tablename__ = "review"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("book.id"), nullable=False)
    rating = Column(Float, nullable=True)
    review_text = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User", back_populates="reviews")
    book = relationship("Book", back_populates="reviews")
