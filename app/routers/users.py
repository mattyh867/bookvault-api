from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.models import User
from app.auth import verify_api_key
from app.schemas import UserCreate, UserUpdate


router = APIRouter()


# ─── GET /users ───────────────────────────────────────────────────────────────
# PROTECTED — listing users requires auth
@router.get(
    "/",
    dependencies=[Depends(verify_api_key)],
    summary="List all users",
    description="Retrieve a paginated list of all users. Requires an **X-API-Key** header."
)
def get_users(
    search: Optional[str] = Query(None, description="Search by username"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(User)

    if search:
        query = query.filter(User.username.ilike(f"%{search}%"))

    total = query.count()
    users = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [format_user(u) for u in users]
    }


# ─── GET /users/{id} ──────────────────────────────────────────────────────────
@router.get(
    "/{user_id}",
    summary="Get a user by ID",
    description="Retrieve a single user's profile and their review count."
)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")
    return format_user(user)


# ─── POST /users ──────────────────────────────────────────────────────────────
@router.post(
    "/",
    status_code=201,
    dependencies=[Depends(verify_api_key)],
    summary="Create a new user",
    description="Register a new user account. Usernames must be unique. Requires an **X-API-Key** header."
)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Username '{payload.username}' is already taken")

    user = User(username=payload.username, password=payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "User created successfully", "user": format_user(user)}


# ─── PUT /users/{id} ──────────────────────────────────────────────────────────
@router.put(
    "/{user_id}",
    dependencies=[Depends(verify_api_key)],
    summary="Update a user",
    description="Update a user's username or password. Only include the fields you want to change. Requires an **X-API-Key** header."
)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return {"message": "User updated successfully", "user": format_user(user)}


# ─── DELETE /users/{id} ───────────────────────────────────────────────────────
@router.delete(
    "/{user_id}",
    dependencies=[Depends(verify_api_key)],
    summary="Delete a user",
    description="Permanently delete a user account and all their reviews. Requires an **X-API-Key** header."
)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")

    db.delete(user)
    db.commit()

    return {"message": f"User '{user.username}' deleted successfully"}


# ─── Helper ───────────────────────────────────────────────────────────────────
def format_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "review_count": len(user.reviews)
    }