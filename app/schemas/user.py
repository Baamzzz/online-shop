"""Pydantic schemas: what the API accepts and returns for users."""
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Data required to register. Validation rejects bad input before it reaches the database."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    """Login credentials."""

    email: EmailStr
    password: str


class UserOut(BaseModel):
    """What the API returns about a user. Deliberatly has no password field."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: str