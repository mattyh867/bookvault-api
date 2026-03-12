"""
BookVault API — Test Suite
==========================
Uses pytest + FastAPI's TestClient to test all endpoints.

How it works:
- We create a SEPARATE SQLite database for testing so your
  real bookvault.db is never touched.
- Before each test, the database is wiped clean and rebuilt with fresh
  tables, so every test is independent.
- We override FastAPI's `get_db` dependency to point at our test DB.

To run:
    pip install pytest httpx
    pytest tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db, Base
from app.models.models import Book, User


# ─── Test Database Setup ──────────────────────────────────────────────────────
# Separate test DB so tests don't affect your real data
TEST_DATABASE_URL = "sqlite:///./test_bookvault.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# This API key must match what your app expects (the fallback in auth.py)
API_KEY = "bookvault-dev-key-123"
AUTH_HEADER = {"X-API-Key": API_KEY}


def override_get_db():
    """Yield a test database session instead of the real one."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Tell FastAPI to use our test DB instead of the real one
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


# ─── Fixtures ─────────────────────────────────────────────────────────────────
# Fixtures run before each test to set up a clean state

@pytest.fixture(autouse=True)
def setup_database():
    """
    Before each test: create all tables fresh.
    After each test: drop everything so the next test starts clean.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def seed_book():
    """Insert a sample book directly into the test DB and return its ID."""
    db = TestSessionLocal()
    book = Book(
        bookID="12345",
        title="East of Eden",
        authors="John Steinbeck",
        average_rating=4.37,
        isbn="0142000655",
        isbn13="9780142000656",
        language_code="eng",
        num_pages=601,
        ratings_count=250000,
        text_reviews_count=5000,
        publication_date="1952",
        publisher="Viking Press",
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    book_id = book.id
    db.close()
    return book_id


@pytest.fixture
def seed_user():
    """Insert a sample user and return their ID."""
    db = TestSessionLocal()
    user = User(username="testuser", password="password123")
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    db.close()
    return user_id


# ═════════════════════════════════════════════════════════════════════════════
# 1. ROOT ENDPOINT
# ═════════════════════════════════════════════════════════════════════════════

class TestRoot:
    """Tests for GET / — the welcome endpoint."""

    def test_root_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_contains_welcome_message(self):
        response = client.get("/")
        data = response.json()
        assert "message" in data
        assert "BookVault" in data["message"]


# ═════════════════════════════════════════════════════════════════════════════
# 2. BOOKS ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

class TestBooks:
    """Tests for /books — CRUD operations and search."""

    # ── GET (Read) ────────────────────────────────────────────────────────

    def test_get_books_empty(self):
        """GET /books on an empty database returns an empty list."""
        response = client.get("/books/")
        assert response.status_code == 200
        assert response.json()["results"] == []

    def test_get_books_returns_seeded_book(self, seed_book):
        """GET /books returns books that exist in the database."""
        response = client.get("/books/")
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    def test_get_book_by_id(self, seed_book):
        """GET /books/{id} returns the correct book."""
        response = client.get(f"/books/{seed_book}")
        assert response.status_code == 200
        assert response.json()["title"] == "East of Eden"

    def test_get_book_not_found(self):
        """GET /books/{id} with a non-existent ID returns 404."""
        response = client.get("/books/99999")
        assert response.status_code == 404

    def test_search_books_by_title(self, seed_book):
        """GET /books?search=eden finds matching books."""
        response = client.get("/books/", params={"search": "eden"})
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    def test_search_books_by_author(self, seed_book):
        """GET /books?search=steinbeck finds matching books by author."""
        response = client.get("/books/", params={"search": "steinbeck"})
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    def test_search_books_no_results(self, seed_book):
        """GET /books?search=zzzzz returns no results."""
        response = client.get("/books/", params={"search": "zzzzz"})
        assert response.json()["total"] == 0

    # ── POST (Create) ────────────────────────────────────────────────────

    def test_create_book_with_auth(self):
        """POST /books with a valid API key creates a book."""
        payload = {
            "title": "Test Book",
            "authors": "Test Author",
            "publisher": "Test Publisher",
        }
        response = client.post("/books/", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 201
        assert response.json()["book"]["title"] == "Test Book"

    def test_create_book_all_fields(self):
        """POST /books with all optional fields populated."""
        payload = {
            "bookID": "9999999",
            "title": "Full Book",
            "authors": "Full Author",
            "average_rating": 4.5,
            "isbn": "1234567890",
            "isbn13": "9781234567890",
            "language_code": "eng",
            "num_pages": 300,
            "ratings_count": 100,
            "text_reviews_count": 10,
            "publication_date": "2025",
            "publisher": "Full Publisher",
        }
        response = client.post("/books/", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 201
        assert response.json()["book"]["authors"] == "Full Author"

    def test_create_book_without_auth(self):
        """POST /books without an API key returns 401."""
        payload = {"title": "No Auth Book", "authors": "Nobody"}
        response = client.post("/books/", json=payload)
        assert response.status_code == 401

    def test_create_book_wrong_key(self):
        """POST /books with an invalid API key returns 403."""
        payload = {"title": "Bad Key Book", "authors": "Nobody"}
        response = client.post("/books/", json=payload, headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 403

    def test_create_book_missing_required_field(self):
        """POST /books without required 'title' field returns 422."""
        payload = {"authors": "No Title Author"}
        response = client.post("/books/", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 422

    # ── PUT (Update) ─────────────────────────────────────────────────────

    def test_update_book(self, seed_book):
        """PUT /books/{id} updates the book's fields."""
        response = client.put(
            f"/books/{seed_book}",
            json={"title": "East of Eden (Updated)"},
            headers=AUTH_HEADER,
        )
        assert response.status_code == 200
        assert "Updated" in response.json()["book"]["title"]

    def test_update_book_not_found(self):
        """PUT /books/{id} on a non-existent book returns 404."""
        response = client.put("/books/99999", json={"title": "Nope"}, headers=AUTH_HEADER)
        assert response.status_code == 404

    # ── DELETE ────────────────────────────────────────────────────────────

    def test_delete_book(self, seed_book):
        """DELETE /books/{id} removes the book."""
        response = client.delete(f"/books/{seed_book}", headers=AUTH_HEADER)
        assert response.status_code == 200
        # Confirm it's gone
        response = client.get(f"/books/{seed_book}")
        assert response.status_code == 404

    def test_delete_book_not_found(self):
        """DELETE /books/{id} on a non-existent book returns 404."""
        response = client.delete("/books/99999", headers=AUTH_HEADER)
        assert response.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# 3. USERS ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

class TestUsers:
    """Tests for /users — CRUD operations."""

    def test_create_user(self):
        """POST /users creates a new user."""
        payload = {"username": "newuser", "password": "secret123"}
        response = client.post("/users/", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 201
        assert response.json()["user"]["username"] == "newuser"

    def test_create_duplicate_user(self, seed_user):
        """POST /users with an existing username returns 409."""
        payload = {"username": "testuser", "password": "anything"}
        response = client.post("/users/", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 409

    def test_get_user_by_id(self, seed_user):
        """GET /users/{id} returns the correct user."""
        response = client.get(f"/users/{seed_user}")
        assert response.status_code == 200
        assert response.json()["username"] == "testuser"

    def test_get_user_not_found(self):
        """GET /users/{id} with a non-existent ID returns 404."""
        response = client.get("/users/99999")
        assert response.status_code == 404

    def test_get_users_requires_auth(self):
        """GET /users without an API key returns 401."""
        response = client.get("/users/")
        assert response.status_code == 401

    def test_get_users_with_auth(self, seed_user):
        """GET /users with a valid API key returns the user list."""
        response = client.get("/users/", headers=AUTH_HEADER)
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    def test_update_user(self, seed_user):
        """PUT /users/{id} updates the user's username."""
        response = client.put(
            f"/users/{seed_user}",
            json={"username": "updated_user"},
            headers=AUTH_HEADER,
        )
        assert response.status_code == 200
        assert response.json()["user"]["username"] == "updated_user"

    def test_delete_user(self, seed_user):
        """DELETE /users/{id} removes the user."""
        response = client.delete(f"/users/{seed_user}", headers=AUTH_HEADER)
        assert response.status_code == 200
        # Confirm they're gone
        response = client.get(f"/users/{seed_user}")
        assert response.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# 4. REVIEWS ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

class TestReviews:
    """Tests for /reviews — CRUD operations and validation."""

    def test_create_review(self, seed_book, seed_user):
        """POST /reviews creates a review linking a user to a book."""
        payload = {
            "book_id": str(seed_book),
            "user_id": seed_user,
            "rating": 9.0,
            "review_text": "A masterpiece of American literature.",
        }
        response = client.post("/reviews/", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 201

    def test_create_duplicate_review(self, seed_book, seed_user):
        """POST /reviews twice for the same user+book returns 409."""
        payload = {"book_id": str(seed_book), "user_id": seed_user, "rating": 8.0}
        client.post("/reviews/", json=payload, headers=AUTH_HEADER)
        response = client.post("/reviews/", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 409

    def test_create_review_invalid_book(self, seed_user):
        """POST /reviews with a non-existent book ID returns 404."""
        payload = {"book_id": "99999", "user_id": seed_user, "rating": 5.0}
        response = client.post("/reviews/", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 404

    def test_create_review_invalid_user(self, seed_book):
        """POST /reviews with a non-existent user ID returns 404."""
        payload = {"book_id": str(seed_book), "user_id": 99999, "rating": 5.0}
        response = client.post("/reviews/", json=payload, headers=AUTH_HEADER)
        assert response.status_code == 404

    def test_get_reviews_empty(self):
        """GET /reviews on an empty database returns an empty list."""
        response = client.get("/reviews/")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_get_reviews_filtered_by_book(self, seed_book, seed_user):
        """GET /reviews?book_id=X returns only reviews for that book."""
        payload = {"book_id": str(seed_book), "user_id": seed_user, "rating": 7.0}
        client.post("/reviews/", json=payload, headers=AUTH_HEADER)

        response = client.get("/reviews/", params={"book_id": str(seed_book)})
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    def test_create_review_without_auth(self, seed_book, seed_user):
        """POST /reviews without an API key returns 401."""
        payload = {"book_id": str(seed_book), "user_id": seed_user, "rating": 5.0}
        response = client.post("/reviews/", json=payload)
        assert response.status_code == 401

    def test_delete_review(self, seed_book, seed_user):
        """DELETE /reviews/{id} removes the review."""
        payload = {"book_id": str(seed_book), "user_id": seed_user, "rating": 6.0}
        create_resp = client.post("/reviews/", json=payload, headers=AUTH_HEADER)
        review_id = create_resp.json()["review"]["id"]

        response = client.delete(f"/reviews/{review_id}", headers=AUTH_HEADER)
        assert response.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# 5. AUTHORS ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

class TestAuthors:
    """Tests for /authors — derived from the books table."""

    def test_get_authors_empty(self):
        """GET /authors on an empty database returns no results."""
        response = client.get("/authors/")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_get_authors_with_book(self, seed_book):
        """GET /authors returns authors derived from books."""
        response = client.get("/authors/")
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    def test_search_authors(self, seed_book):
        """GET /authors?search=steinbeck finds matching authors."""
        response = client.get("/authors/", params={"search": "steinbeck"})
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    def test_get_author_books(self, seed_book):
        """GET /authors/{name}/books returns that author's books."""
        response = client.get("/authors/John Steinbeck/books")
        assert response.status_code == 200
        assert response.json()["book_count"] >= 1

    def test_get_author_books_not_found(self):
        """GET /authors/{name}/books for a non-existent author returns 404."""
        response = client.get("/authors/Nobody Real/books")
        assert response.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# 6. AUTHENTICATION TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestAuthentication:
    """
    Tests that protected endpoints enforce API key auth correctly.
    Covers the three auth states: no key, wrong key, valid key.
    """

    def test_no_key_returns_401(self):
        response = client.post("/books/", json={"title": "X", "authors": "Y"})
        assert response.status_code == 401
        assert "Missing API key" in response.json()["detail"]

    def test_wrong_key_returns_403(self):
        response = client.post(
            "/books/",
            json={"title": "X", "authors": "Y"},
            headers={"X-API-Key": "totally-wrong"},
        )
        assert response.status_code == 403
        assert "Invalid API key" in response.json()["detail"]

    def test_valid_key_allows_access(self):
        response = client.post(
            "/books/",
            json={"title": "Auth Test", "authors": "Tester"},
            headers=AUTH_HEADER,
        )
        assert response.status_code == 201


# ═════════════════════════════════════════════════════════════════════════════
# 7. PAGINATION TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestPagination:
    """Tests that pagination parameters (limit, offset) work correctly."""

    def test_books_pagination_limit(self):
        """Creating 5 books but requesting limit=2 returns only 2."""
        for i in range(5):
            client.post(
                "/books/",
                json={"title": f"Book {i}", "authors": "Author"},
                headers=AUTH_HEADER,
            )
        response = client.get("/books/", params={"limit": 2})
        assert response.status_code == 200
        assert len(response.json()["results"]) == 2
        assert response.json()["total"] == 5  # total count is still 5

    def test_books_pagination_offset(self):
        """Offset skips the first N results."""
        for i in range(5):
            client.post(
                "/books/",
                json={"title": f"Book {i}", "authors": "Author"},
                headers=AUTH_HEADER,
            )
        response = client.get("/books/", params={"limit": 2, "offset": 3})
        assert response.status_code == 200
        assert len(response.json()["results"]) == 2  # books 3 and 4


# ═════════════════════════════════════════════════════════════════════════════
# 8. EDGE CASES & ERROR HANDLING
# ═════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Tests for boundary conditions and error handling."""

    def test_invalid_pagination_limit(self):
        """limit=0 should be rejected by FastAPI validation."""
        response = client.get("/books/", params={"limit": 0})
        assert response.status_code == 422  # Unprocessable Entity

    def test_negative_offset(self):
        """offset=-1 should be rejected by FastAPI validation."""
        response = client.get("/books/", params={"offset": -1})
        assert response.status_code == 422

    def test_review_rating_out_of_range(self):
        """min_rating filter rejects values outside 1-10."""
        response = client.get("/reviews/", params={"min_rating": 11})
        assert response.status_code == 422

    def test_create_book_empty_body(self):
        """POST /books with an empty body returns 422."""
        response = client.post("/books/", json={}, headers=AUTH_HEADER)
        assert response.status_code == 422