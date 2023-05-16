from pydantic import BaseModel
from typing import Optional, Literal


class Review(BaseModel):
    author_name: str
    rating: float
    text: str
    timestamp: float
    image: str | None
    relative_time_description: str


class AddReview(BaseModel):
    rating: int
    text: str


class Restaurant(BaseModel):
    place_id: str
    name: str
    image: str | None
    cuisine: list[str] | None
    rating: float | None
    description: str | None
    gallery: list[str] | None
    reviews: list[Review]
    address: str
    coordinates: list[float]
    phone: str | None
    website: str | None
    opening_hours: str | None
    price_level: str | None
    vegan_friendly: bool | None
    meals: str | None
    favorite: bool


class Attraction(BaseModel):
    place_id: str
    name: str
    image: str | None
    rating: float | None
    description: str | None
    gallery: list[str] | None
    reviews: list[Review]
    address: str
    coordinates: list[float]
    phone: str | None
    website: str | None
    opening_hours: str | None
    price_level: str | None


class RestaurantSearch(BaseModel):
    place_id: str
    name: str
    address: str
    coordinates: list[float]
    image: str | None
    cuisine: list[str] | None
    rating: float | None
    distance: float | None


class AttractionSearch(BaseModel):
    place_id: str
    name: str
    address: str
    coordinates: list[float]
    image: str | None
    rating: float | None
    distance: float | None


class UserProfile(BaseModel):
    first_name: str
    last_name: str
    email: str
    favorites: list[str]
