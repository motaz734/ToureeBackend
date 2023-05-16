import datetime
import math
from typing import List

from geopy.distance import geodesic
import pymongo
from fastapi import APIRouter, Depends
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

import models
from scraping.gmaps_scrapper import get_nearby_places, get_place_details, get_place_photos, get_popular_places
from db_conn import db
from utils import get_relative_time_description

router = APIRouter()


@router.get("/cuisines")
async def get_cuisines():
    cuisines = {"cuisines": {}}
    # get unique cuisines from db
    for cuisines_list in db.Restaurants.find({}, {"cuisine": 1, "_id": 0}):
        for cuisine in cuisines_list["cuisine"]:
            if cuisine not in cuisines["cuisines"]:
                cuisines["cuisines"][cuisine] = cuisines_list['cuisine'][cuisine]
    return cuisines


@router.get('/restaurants/nearby')
async def get_nearby_restaurants(lat: str, lng: str):
    restaurants = get_nearby_places(lat, lng)['results']
    return_data = []

    # process the restaurants and add them to the database
    for restaurant in restaurants:
        place_data = get_place_details(restaurant["place_id"])['result']
        # check if the restaurant is already in the database
        if db.Restaurants.find_one({
            "place_id": restaurant["place_id"]
        }) is None:
            # add the restaurant to the database
            restaurant_db = {
                "name": restaurant["name"],
                "place_id": restaurant["place_id"],
                "description": place_data["editorial_summary"][
                    'overview'] if 'editorial_summary' in place_data else None,
                "location": {
                    "type": "Point",
                    "coordinates": [
                        restaurant["geometry"]["location"]["lng"],
                        restaurant["geometry"]["location"]["lat"]
                    ]
                },
                'cuisine': [],
                'reviews': [],
            }
            db.Restaurants.insert_one(restaurant_db)
        else:
            # grab the data from the database and update it
            db.Restaurants.update_one({
                "place_id": restaurant["place_id"]
            }, {
                "$set": {
                    "name": restaurant["name"],
                    "location": {
                        "type": "Point",
                        "coordinates": [
                            restaurant["geometry"]["location"]["lng"],
                            restaurant["geometry"]["location"]["lat"]
                        ]
                    }
                }
            })
            restaurant_db = db.Restaurants.find_one({
                "place_id": restaurant["place_id"]
            })
        cuisines = [
            cuisine for cuisine in restaurant_db["cuisine"].keys()
        ] if len(restaurant_db["cuisine"]) > 0 else []
        return_data.append(models.RestaurantSearch(
            place_id=restaurant_db["place_id"],
            name=restaurant_db["name"],
            address=place_data["vicinity"],
            coordinates=restaurant_db["location"]["coordinates"],
            image=get_place_photos(place_data["photos"][0]["photo_reference"]) if "photos" in place_data else None,
            cuisine=cuisines,
            rating=restaurant["rating"] if "rating" in restaurant else None,
            distance=geodesic(restaurant_db["location"]["coordinates"], [lng, lat]).meters
        ))

    return {
        "restaurants": return_data
    }


@router.get("/restaurant/{place_id}")
async def get_restaurant(place_id: str, session: SessionContainer = Depends(verify_session())):
    user_id = session.user_id
    # check if the restaurant is favorited
    if db.Users.find_one({
        "user_id": user_id,
        "favorites": place_id
    }) is not None:
        favorite = True
    else:
        favorite = False

    place_data = get_place_details(place_id)['result']
    # get the restaurant from the database
    restaurant = db.Restaurants.find_one({
        "place_id": place_id
    })
    opening_hours = ''
    if 'opening_hours' in place_data:
        for day in place_data["opening_hours"]["weekday_text"]:
            if "Closed" in day:
                opening_hours += f"{day}\n"
                continue
            name, *hours = day.replace('\u202f', ' ').replace('\u2009', ' ').replace('–', '-').split(':')
            start, end = ':'.join(hours).replace(' ', '').split('-')
            opening_hours += f"{name:<10} {start} - {end}\n"
        opening_hours = opening_hours.strip()

    meals = []
    if 'serves_breakfast' in place_data and place_data['serves_breakfast']:
        meals.append('Breakfast')
    if 'serves_lunch' in place_data and place_data['serves_lunch']:
        meals.append('Lunch')
    if 'serves_dinner' in place_data and place_data['serves_dinner']:
        meals.append('Dinner')
    price_levels = {
        0: "Free",
        1: "Inexpensive",
        2: "Moderate",
        3: "Expensive",
        4: "Very Expensive",
    }
    if "price_level" in place_data:
        print(f"{place_data['price_level']=}")
    print(f"{meals=}")
    if "serves_vegetarian_food" in place_data and place_data["serves_vegetarian_food"]:
        print(f"{place_data['serves_vegetarian_food']=}")

    reviews = [
                  models.Review(
                      author_name=review["author_name"],
                      rating=review["rating"],
                      text=review["text"],
                      timestamp=review["timestamp"].timestamp(),
                      relative_time_description=get_relative_time_description(review["timestamp"]),
                      image=None
                  ) for review in restaurant["reviews"]
              ] + [
                  models.Review(
                      author_name=review["author_name"],
                      rating=review["rating"],
                      text=review["text"],
                      timestamp=review["time"],
                      relative_time_description=review["relative_time_description"],
                      image=None
                  ) for review in place_data["reviews"]
              ]

    cuisines = [
        cuisine for cuisine in restaurant["cuisine"].keys()
    ] if len(restaurant["cuisine"]) > 0 else []

    return models.Restaurant(
        place_id=restaurant["place_id"],
        name=restaurant["name"],
        image=get_place_photos(place_data["photos"][0]["photo_reference"]) if "photos" in place_data else None,
        cuisine=cuisines,
        rating=place_data["rating"],
        description=place_data["editorial_summary"]['overview'] if 'editorial_summary' in place_data else None,
        gallery=[get_place_photos(photo["photo_reference"]) for photo in
                 place_data["photos"]] if "photos" in place_data else None,
        reviews=reviews,
        address=place_data["vicinity"],
        coordinates=restaurant["location"]["coordinates"],
        phone=place_data["formatted_phone_number"] if "formatted_phone_number" in place_data else None,
        website=place_data["website"] if "website" in place_data else None,
        opening_hours=opening_hours,
        price_level=price_levels[place_data[
            "price_level"]] + f" ({place_data['price_level'] * '$'})" if "price_level" in place_data else None,
        vegan_friendly=place_data["serves_vegetarian_food"] if "serves_vegetarian_food" in place_data else None,
        meals=', '.join(meals) if len(meals) > 0 else None,
        favorite=favorite
    )


@router.get("/restaurants/")
async def get_restaurants_by_cuisine(lat: float, lng: float, cuisine: str = None, query: str = None):
    # get the restaurants from the database that match the cuisine and sort them by distance
    restaurants = db.Restaurants.aggregate([
        {
            '$geoNear': {
                'near': {
                    'type': 'Point',
                    'coordinates': [
                        lng, lat
                    ]
                },
                'distanceField': 'distance',
                'maxDistance': 50000000,
                'spherical': True
            }
        }, {
            '$match': {
                f"cuisine{'.' + cuisine if cuisine is not None else ''}": {'$exists': True},
                # add a search query if it exists
                'name': {'$regex': query, '$options': 'i'} if query is not None else {'$exists': True}
            }
        }
    ])
    return_data = []
    for restaurant_db in restaurants:
        place_data = get_place_details(restaurant_db["place_id"])['result']
        cuisines = [
            cuisine for cuisine in restaurant_db["cuisine"].keys()
        ] if len(restaurant_db["cuisine"]) > 0 else []
        return_data.append(models.RestaurantSearch(
            place_id=restaurant_db["place_id"],
            name=restaurant_db["name"],
            address=place_data["vicinity"],
            coordinates=restaurant_db["location"]["coordinates"],
            image=get_place_photos(place_data["photos"][0]["photo_reference"]) if "photos" in place_data else None,
            cuisine=cuisines,
            rating=place_data["rating"] if "rating" in place_data else None,
            distance=restaurant_db["distance"]
        ))

    return return_data


@router.get("/restaurants/favorites/")
async def get_favorite_restaurants(lng: float, lat: float, session: SessionContainer = Depends(verify_session())):
    user_id = session.user_id
    # get the restaurants from the database that match the cuisine and sort them by distance
    restaurants = db.Restaurants.aggregate([
        {
            '$match': {
                'place_id': {
                    '$in': db.Users.find_one({
                        "user_id": user_id
                    })["favorites"]
                }
            }
        }
    ])
    return_data = []
    for restaurant_db in restaurants:
        cuisines = [
            cuisine for cuisine in restaurant_db["cuisine"].keys()
        ] if len(restaurant_db["cuisine"]) > 0 else []
        place_data = get_place_details(restaurant_db["place_id"])['result']
        return_data.append(models.RestaurantSearch(
            place_id=restaurant_db["place_id"],
            name=restaurant_db["name"],
            address=place_data["vicinity"],
            coordinates=restaurant_db["location"]["coordinates"],
            image=get_place_photos(place_data["photos"][0]["photo_reference"]) if "photos" in place_data else None,
            cuisine=cuisines,
            rating=place_data["rating"] if "rating" in place_data else None,
            distance=geodesic(restaurant_db["location"]["coordinates"], [lng, lat]).meters
        ))

    return return_data


@router.post("/restaurant/{place_id}/favorite")
async def favorite_restaurant(place_id: str, session: SessionContainer = Depends(verify_session())):
    user_id = session.user_id
    # check if the restaurant is already favorited if it is unfavorite it
    if db.Users.find_one({
        "user_id": user_id,
        "favorites": place_id
    }) is not None:
        db.Users.update_one({
            "user_id": user_id
        }, {
            "$pull": {
                "favorites": place_id
            }
        })
        return {
            "success": True,
            "message": "Restaurant unfavorited"
        }
    db.Users.update_one({
        "user_id": user_id
    }, {
        "$addToSet": {
            "favorites": place_id
        }
    })
    return {
        "success": True,
        "message": "Restaurant favorited"
    }


@router.get("/attractions/")
async def get_nearby_attractions(lat: float, lng: float):
    # TODO: remove 0 rating
    attractions = get_popular_places(lat, lng)["results"]
    return_data = []
    for attraction in attractions:
        distance = geodesic((lat, lng),
                            (attraction["geometry"]["location"]["lat"], attraction["geometry"]["location"]["lng"]))
        return_data.append(models.AttractionSearch(
            place_id=attraction["place_id"],
            name=attraction["name"],
            address=attraction["formatted_address"],
            coordinates=[
                attraction["geometry"]["location"]["lat"], attraction["geometry"]["location"]["lng"]
            ],
            image=get_place_photos(attraction["photos"][0]["photo_reference"]) if "photos" in attraction else None,
            rating=attraction["rating"] if "rating" in attraction else None,
            distance=distance.m
        ))
    return return_data


@router.get("/attractions/{place_id}")
async def get_attraction_details(place_id: str):
    place_data = get_place_details(place_id)['result']
    # get the restaurant from the database
    opening_hours = ''
    if 'opening_hours' in place_data:
        for day in place_data["opening_hours"]["weekday_text"]:
            if "Closed" in day:
                opening_hours += f"{day}\n"
                continue
            name, *hours = day.replace('\u202f', ' ').replace('\u2009', ' ').replace('–', '-').split(':')
            start, end = ':'.join(hours).replace(' ', '').split('-')
            opening_hours += f"{name:<10} {start} - {end}\n"
        opening_hours = opening_hours.strip()

    price_levels = {
        0: "Free",
        1: "Inexpensive",
        2: "Moderate",
        3: "Expensive",
        4: "Very Expensive",
    }
    if "price_level" in place_data:
        print(f"{place_data['price_level']=}")

    reviews = [
        models.Review(
            author_name=review["author_name"],
            rating=review["rating"],
            text=review["text"],
            timestamp=review["time"],
            relative_time_description=review["relative_time_description"],
            image=None
        ) for review in place_data["reviews"]
    ] if "reviews" in place_data else []

    return models.Attraction(
        place_id=place_id,
        name=place_data["name"],
        image=get_place_photos(place_data["photos"][0]["photo_reference"]) if "photos" in place_data else None,
        rating=place_data["rating"],
        description=place_data["editorial_summary"]['overview'] if 'editorial_summary' in place_data else None,
        gallery=[get_place_photos(photo["photo_reference"]) for photo in
                 place_data["photos"]] if "photos" in place_data else None,
        reviews=reviews,
        address=place_data["vicinity"],
        coordinates=[
            place_data["geometry"]["location"]["lat"], place_data["geometry"]["location"]["lng"]
        ],
        phone=place_data["formatted_phone_number"] if "formatted_phone_number" in place_data else None,
        website=place_data["website"] if "website" in place_data else None,
        opening_hours=opening_hours,
        price_level=price_levels[place_data[
            "price_level"]] + f" ({place_data['price_level'] * '$'})" if "price_level" in place_data else None,
    )


@router.get('/profile')
async def get_profile(session: SessionContainer = Depends(verify_session())):
    user_id = session.user_id
    user = db.Users.find_one({
        "user_id": user_id
    })
    return models.UserProfile(
        first_name=user["first_name"],
        last_name=user["last_name"],
        email=user["email"],
        favorites=user["favorites"]
    )


@router.post('/reviews/{place_id}')
async def add_review(place_id: str, review: models.AddReview, session: SessionContainer = Depends(verify_session())):
    user_id = session.user_id
    user = db.Users.find_one({
        "user_id": user_id
    })
    author_name = user["first_name"] + " " + user["last_name"]

    db.Restaurants.update_one({
        "place_id": place_id
    }, {
        "$push": {
            "reviews": {
                "author_name": author_name,
                "author_id": user_id,
                "rating": review.rating,
                "text": review.text,
                "timestamp": datetime.datetime.now()
            }
        }
    })
    return {
        "success": True,
    }


@router.get('/recommendations')
async def get_recommendations(lat: float, lng: float, session: SessionContainer = Depends(verify_session())):
    user_id = session.user_id
    # get user's favorite cuisines
    user = db.Users.find_one({"user_id": user_id})
    # get the cuisines of the restaurants that the user has visited
    favorites = user["favorites"]
    favourite_cuisines = {}
    for fav in favorites:
        restaurant = db.Restaurants.find_one({"place_id": fav})
        for cuisine in restaurant["cuisine"]:
            if cuisine in favourite_cuisines:
                favourite_cuisines[cuisine] += 1
            else:
                favourite_cuisines[cuisine] = 1
    # get the restaurants that have the same cuisine
    recommended_restaurants = []
    # sort the cuisines by the number of times the user has visited a restaurant with that cuisine
    sorted_cuisines = sorted(favourite_cuisines.items(), key=lambda x: x[1], reverse=True)

    index = 0
    while len(recommended_restaurants) < 20:
        if index == len(sorted_cuisines):
            break

        cuisine = sorted_cuisines[index][0]
        restaurants = db.Restaurants.aggregate([
            {"$match": {f"cuisine.{cuisine}": {"$exists": True}}},
            {"$sort": {"rating": -1}},
        ])
        for i, restaurant in enumerate(restaurants):
            if i == 5:
                break
            if restaurant not in recommended_restaurants and restaurant["place_id"] not in favorites:
                recommended_restaurants.append(restaurant)
        index += 1
    return_data = []
    for restaurant in recommended_restaurants:
        place_data = get_place_details(restaurant["place_id"])['result']

        cuisines = [
            cuisine for cuisine in restaurant["cuisine"].keys()
        ] if len(restaurant["cuisine"]) > 0 else []

        return_data.append(models.RestaurantSearch(
            place_id=restaurant["place_id"],
            name=restaurant["name"],
            address=place_data["vicinity"],
            coordinates=restaurant["location"]["coordinates"],
            image=get_place_photos(place_data["photos"][0]["photo_reference"]) if "photos" in place_data else None,
            cuisine=cuisines,
            rating=place_data["rating"] if "rating" in place_data else None,
            distance=geodesic(restaurant["location"]["coordinates"], [lng, lat]).meters
        ))
    return return_data


@router.get('/reviews/my_reviews/')
async def get_my_reviews(session: SessionContainer = Depends(verify_session())):
    user_id = session.user_id
    user = db.Users.find_one({"user_id": user_id})
    reviews = []
    for fav in user["favorites"]:
        restaurant = db.Restaurants.find_one({"place_id": fav})
        for review in restaurant["reviews"]:
            if review["author_id"] == user_id:
                reviews.append(models.Review(
                    author_name=review["author_name"],
                    rating=review["rating"],
                    text=review["text"],
                    timestamp=review["timestamp"].timestamp(),
                    relative_time_description=get_relative_time_description(review["timestamp"]),
                    image=None
                ))
    return reviews