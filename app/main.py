from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager

from app.database import engine, SessionLocal
from app.models.models import Base, Book
from app.routers import books, reviews, authors, users, analytics
from data.import_data import run_import

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Book).count() == 0:
            print("Database empty — seeding...")
            run_import("data/booksnew.csv")
    finally:
        db.close()
    yield

app = FastAPI(
    title="BookVault API",
    lifespan=lifespan,
    description="""...""",
    version="1.0.0",
)

app.include_router(books.router, prefix="/books", tags=["Books"])
app.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])
app.include_router(authors.router, prefix="/authors", tags=["Authors"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])

@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to BookVault API",
        "docs": "/docs",
        "version": "1.0.0"
    }

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {})
    schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    protected_gets = ["/users/"]
    for path, methods in schema.get("paths", {}).items():
        for method, operation in methods.items():
            if method in ("post", "put", "delete", "patch"):
                operation["security"] = [{"ApiKeyAuth": []}]
            elif method == "get" and path in protected_gets:
                operation["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi