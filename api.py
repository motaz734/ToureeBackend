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

restaurants_data = {
    "Burger King": {
        'name': 'Burger King',
        'image': 'http://placehold.it/128x128',
        'cuisine': 'American',
        'rating': 4.5,
        'description': "Burger King is an American global chain of hamburger fast food restaurants. Headquartered in the unincorporated area of Miami-Dade County, Florida, the company was founded in 1953 as Insta-Burger King, a Jacksonville, Florida-based restaurant chain. After Insta-Burger King ran into financial difficulties in 1954, its two Miami-based franchisees David Edgerton and James McLamore purchased the company and renamed it Burger King. In 1957, the first Burger King restaurant outside of Florida was opened in Jacksonville. In 1967, Burger King moved its headquarters to Miami. In 1974, Burger King purchased Canadian-based Popeyes Famous Fried Chicken and changed its name to Burger King Corporation. Popeyes was spun off in 1993, and the company returned to its original name. In 2010, 3G Capital of Brazil acquired a majority stake in the company. In 2014, Burger King purchased Canadian coffee and doughnut chain Tim Hortons in a deal valued at US$11 billion. In 2016, Burger King changed its corporate structure to a Dutch company, Burger King Holdings Inc., which is based in Canada. In 2017, Burger King announced plans to move its headquarters to Canada.",
        'menu': [
            'http://placehold.it/1000x1000',
            'http://placehold.it/1000x1000',
            'http://placehold.it/1000x1000',
        ],
        'branches': [
            {
                'name': 'Burger King - 1',
                'address': 'Burger King - 1',
            }
        ],
        'gallery': [
            'http://placehold.it/1000x1000',
            'http://placehold.it/1000x1000',
            'http://placehold.it/1000x1000',
        ],
        'ratings': [
            {
                'user': 'user1',
                'rating': 4.5,
                'review': 'Good food',
            },
        ],
        'contacts': [
            {
                'name': 'Burger King - 1',
                'address': 'Burger King - 1',
                'phone': 'Burger King - 1',
            }
        ],
    },
    'McDonalds': {
        'name': 'McDonalds',
        'image': 'http://placehold.it/128x128',
        'cuisine': 'American',
        'rating': 4.5,
    },
    'KFC': {
        'name': 'KFC',
        'image': 'http://placehold.it/128x128',
        'cuisine': 'American',
        'rating': 4.5,
    },
    'Pizza Hut': {
        'name': 'Pizza Hut',
        'image': 'http://placehold.it/128x128',
        'cuisine': 'American',
        'rating': 4.5,
    },
    "Joy Luck": {
        "name": "Joy Luck",
        "image": "https://lh5.googleusercontent.com/p/AF1QipMBe6xAS5z8ewwJHABdp979XaOdeqOcmRvOuaEC=w426-h240-k-no",
        "cuisine": "Chinese",
        "rating": 4.0,
        "description": "",
        "menu": [
            "https://lh5.googleusercontent.com/p/AF1QipN7kalhI7S9Y_kQL69qRCQXJpgoXbCREiSWnHXQ=w203-h152-k-no",
            "https://lh5.googleusercontent.com/p/AF1QipM-keN2bQoPtQUp2mNYKrxz3UnrC3UBivBj4GPL=w203-h270-k-no",
            "https://lh5.googleusercontent.com/p/AF1QipOhyy3f2nPRu1GpCaMucl5XY9mzJ1fKG34HvhTk=w203-h152-k-no",
            "https://lh5.googleusercontent.com/p/AF1QipPYxgZbXZrIY5d_Oygy5gBm14nJpUrV4u97lwPI=w203-h270-k-no",
            "https://lh5.googleusercontent.com/p/AF1QipM60Nb9QlIcKkxE_hII_H3dbGZEbT3TtcyGgD6v=w203-h152-k-no",
            "https://lh5.googleusercontent.com/p/AF1QipPtPpczLj3IMx48zDS44pFxz0nsBfFkQSLA3R5h=w203-h270-k-no",
            "https://lh5.googleusercontent.com/p/AF1QipMWZpiVrxY4GNL9hpyupgNb__uNuZPtRYev5dRh=w203-h168-k-no",
            "https://lh5.googleusercontent.com/p/AF1QipMEXIL2hc434uxCf--KpzsSHXKPZ4EXA5YUGZtg=w203-h270-k-no",
            "https://lh5.googleusercontent.com/p/AF1QipOISChZ3-xqMppGKja-35Tqvfp7HA8rmglbJ5_p=w203-h163-k-no",
        ],
        "branches": [
            {
                "name": "Maadi Branch 1",
                "address": "X77M+5FG, Naguib Mahfouz, Maadi as Sarayat Al Gharbeyah, Maadi, Cairo Governorate 4213215",
                "human_address": "13 Road 233, Degla Maadi, Maadi, Cairo Governorate, Egypt",
                "contacts": ["01222767788", "0225165105"],
                "working_hours": "11:00 AM - 10:00 PM",
            },
            {
                "name": "Maadi Branch 2",
                "address": "X77M+5FG، نجيب محفوظ، معادي السرايات الغربية، قسم المعادي، محافظة القاهرة‬ 4213215",
                "human_address": "28 Naguib Mahfouz Street, 1st Floor, Nirco Buildings ",
                "contacts": ["0225216809"],
                "working_hours": "11:00 AM - 10:00 PM",
            }
        ],
        "gallery": [
            "http://placehold.it/1000x1000",
            "http://placehold.it/1000x1000",
            "http://placehold.it/1000x1000",
        ],
        "ratings": [],
    },

}


@router.get("/cuisines")
async def get_cuisines():
    cuisines = {"cuisines": {}}
    for restaurant in db.Restaurants.distinct("cuisine"):
        if restaurant == "null":
            continue
        cuisines['cuisines'][restaurant] = "http://placehold.it/128x128"
    return cuisines


@router.get('/restaurants/nearby')
async def get_nearby_restaurants(lat: str, lng: str):
    # restaurants = get_nearby_places(lat, lng)['results']
    restaurants = [
        {'business_status': 'OPERATIONAL', 'geometry': {'location': {'lat': 29.9606553, 'lng': 31.2783435},
                                                        'viewport': {'northeast': {'lat': 29.9620042802915,
                                                                                   'lng': 31.27967313029149},
                                                                     'southwest': {'lat': 29.9593063197085,
                                                                                   'lng': 31.27697516970849}}},
         'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
         'icon_background_color': '#FF9E67',
         'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
         'name': 'Bab El Hadid', 'opening_hours': {'open_now': True}, 'photos': [{'height': 867,
                                                                                  'html_attributions': [
                                                                                      '<a href="https://maps.google.com/maps/contrib/104390064466555286051">Bab El Hadid</a>'],
                                                                                  'photo_reference': 'AUjq9jk4SEkJ3QcTh2QsrL0tsE3ITfffpEWtM5M-AulUzvu83Ygagk5kckShxbo1TuPciYCjAXvlssoSZStXoW4qlN9GF-ixvipMz0Jgp5jygNsxWRh9GQoQqkGn0jpxWcIjQGSBRJ9V22w0yA67UE4EAMwaFk_TynFz5MqS_V4p7MWwz3E2',
                                                                                  'width': 1156}],
         'place_id': 'ChIJaywaszI5WBQR-8P_9OdlJpQ',
         'plus_code': {'compound_code': 'X76H+78 Maadi, Egypt', 'global_code': '7GXHX76H+78'}, 'rating': 4.1,
         'reference': 'ChIJaywaszI5WBQR-8P_9OdlJpQ', 'scope': 'GOOGLE',
         'types': ['restaurant', 'food', 'point_of_interest', 'establishment'], 'user_ratings_total': 13,
         'vicinity': '19 Street 233, Maadi as Sarayat Al Gharbeyah, Maadi'},
        {'business_status': 'OPERATIONAL', 'geometry': {'location': {'lat': 29.9606501, 'lng': 31.2784151},
                                                        'viewport': {'northeast': {'lat': 29.9619990802915,
                                                                                   'lng': 31.27974583029149},
                                                                     'southwest': {'lat': 29.9593011197085,
                                                                                   'lng': 31.2770478697085}}},
         'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
         'icon_background_color': '#FF9E67',
         'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
         'name': 'الواحي', 'opening_hours': {'open_now': True}, 'photos': [{'height': 4000,
                                                                            'html_attributions': [
                                                                                '<a href="https://maps.google.com/maps/contrib/112814543450581287439">박창영</a>'],
                                                                            'photo_reference': 'AUjq9jmTQAetXflp_3jcH7GuqiQ0aGfklxgjQtJfwTu333OTp4SOL9BSRtTKfMXnCOi5BJn2eYRp7rZjPPPoiCP8YQV2oROq-OjXEmz_0iLH4b8LjoBb62C27skMzGXxKKBhKQYg3cgAS5W78uQ26Xgz2ewIPsdUg-waWujFm0o42xhHC4vC',
                                                                            'width': 3000}],
         'place_id': 'ChIJJZjcuMM5WBQRkbJbNbtVRkY',
         'plus_code': {'compound_code': 'X76H+79 Maadi, Egypt', 'global_code': '7GXHX76H+79'}, 'rating': 4.5,
         'reference': 'ChIJJZjcuMM5WBQRkbJbNbtVRkY', 'scope': 'GOOGLE',
         'types': ['restaurant', 'food', 'point_of_interest', 'establishment'], 'user_ratings_total': 77,
         'vicinity': '19 Street 233, Maadi as Sarayat Al Gharbeyah, Maadi'},
        {'business_status': 'OPERATIONAL', 'geometry': {'location': {'lat': 29.9607357, 'lng': 31.278628},
                                                        'viewport': {'northeast': {'lat': 29.9620847302915,
                                                                                   'lng': 31.2798432302915},
                                                                     'southwest': {'lat': 29.9593867697085,
                                                                                   'lng': 31.2771452697085}}},
         'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
         'icon_background_color': '#FF9E67',
         'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
         'name': 'دار دمشق', 'opening_hours': {'open_now': True}, 'place_id': 'ChIJiVvsvmw4WBQR_QwN10oBhLs',
         'rating': 4.5, 'reference': 'ChIJiVvsvmw4WBQR_QwN10oBhLs', 'scope': 'GOOGLE',
         'types': ['restaurant', 'food', 'point_of_interest', 'establishment'], 'user_ratings_total': 2,
         'vicinity': 'X76H+7FR, Street 233, مساكن المعادى, قسم المعادى'}, {'business_status': 'OPERATIONAL',
                                                                           'geometry': {'location': {
                                                                               'lat': 29.9598573,
                                                                               'lng': 31.2786189},
                                                                               'viewport': {
                                                                                   'northeast': {
                                                                                       'lat': 29.96120618029149,
                                                                                       'lng': 31.2800656802915},
                                                                                   'southwest': {
                                                                                       'lat': 29.9585082197085,
                                                                                       'lng': 31.2773677197085}}},
                                                                           'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
                                                                           'icon_background_color': '#FF9E67',
                                                                           'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
                                                                           'name': '餃子屋 ダックハウス',
                                                                           'opening_hours': {
                                                                               'open_now': True},
                                                                           'place_id': 'ChIJu8Mzy2w4WBQREh6xU8usCyM',
                                                                           'rating': 4.5,
                                                                           'reference': 'ChIJu8Mzy2w4WBQREh6xU8usCyM',
                                                                           'scope': 'GOOGLE',
                                                                           'types': ['restaurant', 'food',
                                                                                     'point_of_interest',
                                                                                     'establishment'],
                                                                           'user_ratings_total': 2,
                                                                           'vicinity': 'X75H+WCX, Maadi as Sarayat Al Gharbeyah, Maadi'},
        {'business_status': 'OPERATIONAL', 'geometry': {'location': {'lat': 29.9597879, 'lng': 31.2781724},
                                                        'viewport': {'northeast': {'lat': 29.96113673029149,
                                                                                   'lng': 31.27956123029149},
                                                                     'southwest': {'lat': 29.95843876970849,
                                                                                   'lng': 31.27686326970849}}},
         'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
         'icon_background_color': '#FF9E67',
         'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
         'name': '烤鸭坊', 'opening_hours': {'open_now': True}, 'photos': [{'height': 4096,
                                                                            'html_attributions': [
                                                                                '<a href="https://maps.google.com/maps/contrib/103565867936339505830">Mahmoud Ahmed</a>'],
                                                                            'photo_reference': 'AUjq9jkJo2ObWYB-_tz2qDs24P4UxJ9CNPha_-x5BTtNoxZ7ZigVRU3cIz2WP-WPXxiFZL0ltxCL6wELCFm4_kksoXuxNZaeU7WZHdNZ9oiLjfDj2QPPJXk5wvLHfiUr4-wpqwjKd4rkGf7PsZUSIpcpf8qDTMyFzlyG-K2MDApdHDPNTg5t',
                                                                            'width': 3072}],
         'place_id': 'ChIJ46ddIxk5WBQRlhf9MVR-p_E',
         'plus_code': {'compound_code': 'X75H+W7 Maadi, Egypt', 'global_code': '7GXHX75H+W7'}, 'rating': 4.4,
         'reference': 'ChIJ46ddIxk5WBQRlhf9MVR-p_E', 'scope': 'GOOGLE',
         'types': ['restaurant', 'food', 'point_of_interest', 'establishment'], 'user_ratings_total': 25,
         'vicinity': '233،, Maadi as Sarayat Al Gharbeyah, Maadi'}, {'business_status': 'OPERATIONAL',
                                                                     'geometry': {
                                                                         'location': {'lat': 29.9609049,
                                                                                      'lng': 31.2782859},
                                                                         'viewport': {'northeast': {
                                                                             'lat': 29.9622537302915,
                                                                             'lng': 31.2796495302915},
                                                                             'southwest': {
                                                                                 'lat': 29.9595557697085,
                                                                                 'lng': 31.2769515697085}}},
                                                                     'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
                                                                     'icon_background_color': '#FF9E67',
                                                                     'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
                                                                     'name': 'Bun Shawarma',
                                                                     'opening_hours': {'open_now': True},
                                                                     'photos': [{'height': 1600,
                                                                                 'html_attributions': [
                                                                                     '<a href="https://maps.google.com/maps/contrib/112274892758663457321">Bun Shawarma</a>'],
                                                                                 'photo_reference': 'AUjq9jnyoMrzAiF7jTB4MwBCO2SX7ZITNOj76wGFBvJZZpeUEbPSnZMvRcJGzH3OL94mAeh2LLD1l156an56kvXJhJ-qMBxF0mEiQRc5LHmQzHdLkndiONb9GV03FyMCjrx_a_6VdxPxH75fhw0wbRlncw9GYI-fZ0tN9UYYJ0GZ1xES33Pr',
                                                                                 'width': 1330}],
                                                                     'place_id': 'ChIJO2X-GW45WBQROcx-CiAoCBg',
                                                                     'plus_code': {
                                                                         'compound_code': 'X76H+98 Maadi, Egypt',
                                                                         'global_code': '7GXHX76H+98'},
                                                                     'rating': 4.8,
                                                                     'reference': 'ChIJO2X-GW45WBQROcx-CiAoCBg',
                                                                     'scope': 'GOOGLE',
                                                                     'types': ['restaurant', 'food',
                                                                               'point_of_interest',
                                                                               'establishment'],
                                                                     'user_ratings_total': 11,
                                                                     'vicinity': '19, 233 St, Degla Square, Maadi'},
        {'business_status': 'OPERATIONAL',
         'geometry': {'location': {'lat': 29.96079559999999, 'lng': 31.2777142},
                      'viewport': {'northeast': {'lat': 29.96213808029149, 'lng': 31.2789494302915},
                                   'southwest': {'lat': 29.9594401197085, 'lng': 31.2762514697085}}},
         'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
         'icon_background_color': '#FF9E67',
         'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
         'name': 'Sweets Fun Restaurant & Cafe', 'opening_hours': {'open_now': True}, 'photos': [
            {'height': 720, 'html_attributions': [
                '<a href="https://maps.google.com/maps/contrib/106768920055985464207">Abdelrhman Galil</a>'],
             'photo_reference': 'AUjq9jmPu0h3zWOSdSk0j4VP1IJtkTKreS4wTJulnQn5r3ZEx-LkixGZczsZF549V2p0mPYkYpU_NNcnJrMrD8if8Uxds1-7JvXanWXpo14ClTuHMs4sZmqSUFRXPleP-M48lLUTvgUy6R6mIGluh2HZDXrjmCmj6JBmKpOjV6z1bJ5oI3TU',
             'width': 1280}], 'place_id': 'ChIJn6InFpY5WBQRqQmrA4edexk', 'rating': 5,
         'reference': 'ChIJn6InFpY5WBQRqQmrA4edexk', 'scope': 'GOOGLE',
         'types': ['restaurant', 'food', 'point_of_interest', 'establishment'], 'user_ratings_total': 6,
         'vicinity': 'X76H+838, Street 232, Maadi as Sarayat Al Gharbeyah, digla'},
        {'business_status': 'OPERATIONAL',
         'geometry': {'location': {'lat': 29.95963399999999, 'lng': 31.27815089999999},
                      'viewport': {'northeast': {'lat': 29.9609832302915, 'lng': 31.27955063029149},
                                   'southwest': {'lat': 29.9582852697085, 'lng': 31.27685266970849}}},
         'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
         'icon_background_color': '#FF9E67',
         'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
         'name': 'Fox Coffee & Restaurant', 'opening_hours': {'open_now': True}, 'photos': [{'height': 3024,
                                                                                             'html_attributions': [
                                                                                                 '<a href="https://maps.google.com/maps/contrib/104090993361951920384">Ramy Amer</a>'],
                                                                                             'photo_reference': 'AUjq9jkrbN28SB5tz1qkfnEycvdglyhGp_GZGZQwwh42yjdPm7WbCiHJEEQVmOvmZLqxmygdbXxmB9NYfixmbiYtn1DyqcGJLf4f4VUI-JXrqenb3ngyuiR62Eo9jGntbqEgpjB6JmTu1tPgx-jNCZI7_m3sLbCoKxoqHZ5ipGJQX_sjQBDM',
                                                                                             'width': 4032}],
         'place_id': 'ChIJ6W-yymw4WBQR1X_rrtZzobI',
         'plus_code': {'compound_code': 'X75H+V7 Maadi, Egypt', 'global_code': '7GXHX75H+V7'},
         'price_level': 2, 'rating': 4.3, 'reference': 'ChIJ6W-yymw4WBQR1X_rrtZzobI', 'scope': 'GOOGLE',
         'types': ['restaurant', 'food', 'point_of_interest', 'establishment'], 'user_ratings_total': 452,
         'vicinity': '233، معادي السرايات الغربية، المعادي،'}, {'business_status': 'OPERATIONAL',
                                                                'geometry': {
                                                                    'location': {'lat': 29.96049590000001,
                                                                                 'lng': 31.27729660000001},
                                                                    'viewport': {'northeast': {
                                                                        'lat': 29.9617413802915,
                                                                        'lng': 31.2786591802915},
                                                                        'southwest': {
                                                                            'lat': 29.9590434197085,
                                                                            'lng': 31.2759612197085}}},
                                                                'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
                                                                'icon_background_color': '#FF9E67',
                                                                'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
                                                                'name': 'Crave',
                                                                'opening_hours': {'open_now': True},
                                                                'photos': [{'height': 4032,
                                                                            'html_attributions': [
                                                                                '<a href="https://maps.google.com/maps/contrib/106867111138081617543">Sedra Abumoustafa</a>'],
                                                                            'photo_reference': 'AUjq9jmUpL-XHz72nK-X2IUYxHs2Gf_eUPjR7ZEYL-3bpX--PN3MmFZpqv_qsG2c253ePRm9L9h-9MXVO5yjZKZC-hHRJDpQYozZyIBYBVbAIAniTyHc5-oNoMxCgTMpgF9aYlQc5I0egE-V7lvGJluxrO5p1puojriBFQA4DM940jfJsz_y',
                                                                            'width': 3024}],
                                                                'place_id': 'ChIJ3eYwXA04WBQR7IlToJY9F6E',
                                                                'plus_code': {
                                                                    'compound_code': 'X76G+5W Maadi, Egypt',
                                                                    'global_code': '7GXHX76G+5W'},
                                                                'price_level': 2, 'rating': 4.3,
                                                                'reference': 'ChIJ3eYwXA04WBQR7IlToJY9F6E',
                                                                'scope': 'GOOGLE',
                                                                'types': ['restaurant', 'food',
                                                                          'point_of_interest',
                                                                          'establishment'],
                                                                'user_ratings_total': 1711,
                                                                'vicinity': 'Street 213, Maadi as Sarayat Al Gharbeyah, Maadi'},
        {'business_status': 'OPERATIONAL',
         'geometry': {'location': {'lat': 29.9610192, 'lng': 31.27757260000001},
                      'viewport': {'northeast': {'lat': 29.9623712802915, 'lng': 31.2789666802915},
                                   'southwest': {'lat': 29.9596733197085, 'lng': 31.2762687197085}}},
         'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
         'icon_background_color': '#FF9E67',
         'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
         'name': 'KoKio fried chicken', 'opening_hours': {'open_now': True}, 'photos': [{'height': 3024,
                                                                                         'html_attributions': [
                                                                                             '<a href="https://maps.google.com/maps/contrib/106846055432417869605">Explore MyHood</a>'],
                                                                                         'photo_reference': 'AUjq9jlwWlpUQxUu4XJG6g-ucHBT1h_kQyuOeaFRKTVoqIjc79-3hvO-FmV4iBxFNDZUwl4jeOY4jZgu6TCflIoTzxGwtCmt3Q28ADdw-hqjLCq7_a2-2E5S-ztpgnZ47Ii64anLXu0JE0RqvgFfyD-lkcOhtzFjfjYwZvWayuhndir7IBRn',
                                                                                         'width': 4032}],
         'place_id': 'ChIJ743C3Gw4WBQRfV3H6VHiMaQ', 'rating': 4.3,
         'reference': 'ChIJ743C3Gw4WBQRfV3H6VHiMaQ', 'scope': 'GOOGLE',
         'types': ['restaurant', 'food', 'point_of_interest', 'establishment'], 'user_ratings_total': 1023,
         'vicinity': 'X76H+C24, Maadi as Sarayat Al Gharbeyah, Maadi'}, {'business_status': 'OPERATIONAL',
                                                                         'geometry': {
                                                                             'location': {'lat': 29.9603194,
                                                                                          'lng': 31.2771528},
                                                                             'viewport': {'northeast': {
                                                                                 'lat': 29.9616528802915,
                                                                                 'lng': 31.27850388029149},
                                                                                 'southwest': {
                                                                                     'lat': 29.9589549197085,
                                                                                     'lng': 31.2758059197085}}},
                                                                         'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
                                                                         'icon_background_color': '#FF9E67',
                                                                         'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
                                                                         'name': "Marny's",
                                                                         'opening_hours': {'open_now': True},
                                                                         'photos': [{'height': 829,
                                                                                     'html_attributions': [
                                                                                         '<a href="https://maps.google.com/maps/contrib/103596549399695348795">MARNY&#39;S Restaurant Co</a>'],
                                                                                     'photo_reference': 'AUjq9jmfn3NxhqY8SnUIGo54QzkoaWPxJAYggqJ3mebx_6OzhrvPKgfvpN4oxQtdYBDIg7Nhm0pnIvXr_RgH1BXMtQS18XdYvKYdH1PR6ehesOfOK1xghzdhmp1IDaQ0XY_UpbrG-jubmcRwdh2-qCKKO34gkEegV3EGXoojvDgpezEdGDas',
                                                                                     'width': 1125}],
                                                                         'place_id': 'ChIJYSUiK204WBQRd08AZN_rcFE',
                                                                         'plus_code': {
                                                                             'compound_code': 'X76G+4V Maadi, Egypt',
                                                                             'global_code': '7GXHX76G+4V'},
                                                                         'price_level': 2, 'rating': 4.3,
                                                                         'reference': 'ChIJYSUiK204WBQRd08AZN_rcFE',
                                                                         'scope': 'GOOGLE',
                                                                         'types': ['restaurant', 'food',
                                                                                   'point_of_interest',
                                                                                   'establishment'],
                                                                         'user_ratings_total': 307,
                                                                         'vicinity': '٣٢ Street 213, ثكنات, Maadi'},
        {'business_status': 'OPERATIONAL', 'geometry': {'location': {'lat': 29.9603475, 'lng': 31.2771435},
                                                        'viewport': {'northeast': {'lat': 29.96165878029149,
                                                                                   'lng': 31.2784974302915},
                                                                     'southwest': {'lat': 29.9589608197085,
                                                                                   'lng': 31.2757994697085}}},
         'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
         'icon_background_color': '#FF9E67',
         'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
         'name': 'Cairo 80th Grills كبابجي القاهرة 80', 'opening_hours': {'open_now': True}, 'photos': [
            {'height': 1440, 'html_attributions': [
                '<a href="https://maps.google.com/maps/contrib/104668369363927805791">mostafa okasha</a>'],
             'photo_reference': 'AUjq9jndDVlREXAgdzWuWcSoxhmU4yxR-OFFMd5IvInmak8YRz1rd3kUBc3NzA5aiOEjES273NMJujLhRQUO6nxUMxYs6MJS2KQCYrB7-oX_7-VMNYoKVzihD8JagLFvUejdpFkxHkApc9ybcbYanbNwhwCGyi9rVamlx5s1ivjHh7HsprSV',
             'width': 1080}], 'place_id': 'ChIJoaKrB0k5WBQROPD6uGKazpE',
         'plus_code': {'compound_code': 'X76G+4V Maadi, Egypt', 'global_code': '7GXHX76G+4V'}, 'rating': 3.4,
         'reference': 'ChIJoaKrB0k5WBQROPD6uGKazpE', 'scope': 'GOOGLE',
         'types': ['restaurant', 'food', 'point_of_interest', 'establishment'], 'user_ratings_total': 42,
         'vicinity': 'Villa 36, 213 Street, Degla Square, قسم المعادي'}, {'business_status': 'OPERATIONAL',
                                                                          'geometry': {
                                                                              'location': {'lat': 29.9599113,
                                                                                           'lng': 31.2770785},
                                                                              'viewport': {'northeast': {
                                                                                  'lat': 29.9613313802915,
                                                                                  'lng': 31.27833628029149},
                                                                                  'southwest': {
                                                                                      'lat': 29.9586334197085,
                                                                                      'lng': 31.2756383197085}}},
                                                                          'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
                                                                          'icon_background_color': '#FF9E67',
                                                                          'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
                                                                          'name': 'Sizzler Steak House (Maadi)',
                                                                          'opening_hours': {
                                                                              'open_now': True}, 'photos': [
                {'height': 2176, 'html_attributions': [
                    '<a href="https://maps.google.com/maps/contrib/115294696473887123457">Ahmad Abd-Allah</a>'],
                 'photo_reference': 'AUjq9jl5Lr2TZuuQVQwzA5ODTJrPxkuYwSMJcFFJJj7AxUGcuIaK6eQKU8mGXdF1v6e7kmotRPya4QPmiBXx5jaTYznW4kLSw30XjVqI3jYaDUBcedtLO9l9R2iZH-yIDv71p4Q1Vbwhq1_Kp2X039wbVh4R617Sd-QISF9wiBtwPXnHrtlc',
                 'width': 4608}], 'place_id': 'ChIJ3UuKKRM4WBQRZO4yVy-oXOc', 'plus_code': {
                'compound_code': 'X75G+XR Maadi, Egypt', 'global_code': '7GXHX75G+XR'}, 'price_level': 2, 'rating': 4.6,
                                                                          'reference': 'ChIJ3UuKKRM4WBQRZO4yVy-oXOc',
                                                                          'scope': 'GOOGLE',
                                                                          'types': ['restaurant', 'food',
                                                                                    'point_of_interest',
                                                                                    'establishment'],
                                                                          'user_ratings_total': 3210,
                                                                          'vicinity': '17 Road 231 Maadi Degla'},
        {'business_status': 'OPERATIONAL', 'geometry': {'location': {'lat': 29.9597112, 'lng': 31.2771357},
                                                        'viewport': {'northeast': {'lat': 29.9610556802915,
                                                                                   'lng': 31.2783710802915},
                                                                     'southwest': {'lat': 29.9583577197085,
                                                                                   'lng': 31.2756731197085}}},
         'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
         'icon_background_color': '#FF9E67',
         'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
         'name': 'La Rosa', 'opening_hours': {'open_now': True}, 'photos': [{'height': 3968,
                                                                             'html_attributions': [
                                                                                 '<a href="https://maps.google.com/maps/contrib/104476186581613561083">Sarah Belal</a>'],
                                                                             'photo_reference': 'AUjq9jnXwQlr4O8z_mzdVScDS1xbZoq0hW7HTSdSCPwOjrffl2yTrgxVUJHjwFbDZGVpa1ptiQZtrbnJBAElvJ8gIcA6xU3iXYdx4YvhePPuAHnaejRcW120Rl89Qq5pMYLExZIcWxMO7vHz6eRKWMrmWfFjsYel3_wvzVO4tj2Yk1zATBBy',
                                                                             'width': 2976}],
         'place_id': 'ChIJBbLkJhM4WBQRzvmubA20ukc',
         'plus_code': {'compound_code': 'X75G+VV Maadi, Egypt', 'global_code': '7GXHX75G+VV'},
         'price_level': 2, 'rating': 4.3, 'reference': 'ChIJBbLkJhM4WBQRzvmubA20ukc', 'scope': 'GOOGLE',
         'types': ['restaurant', 'food', 'point_of_interest', 'establishment'], 'user_ratings_total': 292,
         'vicinity': '19 Street 231, Maadi as Sarayat Al Gharbeyah, Maadi'},
        {'business_status': 'OPERATIONAL', 'geometry': {'location': {'lat': 29.9602742, 'lng': 31.2769339},
                                                        'viewport': {'northeast': {'lat': 29.9616309802915,
                                                                                   'lng': 31.2782818802915},
                                                                     'southwest': {'lat': 29.9589330197085,
                                                                                   'lng': 31.2755839197085}}},
         'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
         'icon_background_color': '#FF9E67',
         'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
         'name': 'كبابجي القاهرة 70 Cairo 70th Grills', 'opening_hours': {'open_now': True}, 'photos': [
            {'height': 2048, 'html_attributions': [
                '<a href="https://maps.google.com/maps/contrib/111862982732620321829">كبابجي القاهرة 70 Cairo 70th Grills</a>'],
             'photo_reference': 'AUjq9jlmxZqh4df4nB2k6zRqsJeEvWCFu5bGmU76q618inCmS3kw3jeBOXbQ4qAwCDXW01q-erRZMYO1OLst8uufb1ojv-rsBMel4LBQiFurodPRG8qfAiHpuC8klsfcYccAiSAk1qXkCymbJv4KJAlycuOZUdg5yyWTaGw_mayBMGgIcUIo',
             'width': 1536}], 'place_id': 'ChIJ0ap2fCM5WBQR3Dh5zTZ5j2c',
         'plus_code': {'compound_code': 'X76G+4Q Maadi, Egypt', 'global_code': '7GXHX76G+4Q'}, 'rating': 4.4,
         'reference': 'ChIJ0ap2fCM5WBQR3Dh5zTZ5j2c', 'scope': 'GOOGLE',
         'types': ['restaurant', 'food', 'point_of_interest', 'establishment'], 'user_ratings_total': 7,
         'vicinity': 'Street 213'}, {'business_status': 'OPERATIONAL',
                                     'geometry': {'location': {'lat': 29.9597636, 'lng': 31.2770765},
                                                  'viewport': {'northeast': {'lat': 29.9611091802915,
                                                                             'lng': 31.2783400802915},
                                                               'southwest': {'lat': 29.9584112197085,
                                                                             'lng': 31.2756421197085}}},
                                     'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
                                     'icon_background_color': '#FF9E67',
                                     'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
                                     'name': 'Cairo kitchen maadi', 'opening_hours': {'open_now': True},
                                     'photos': [{'height': 809, 'html_attributions': [
                                         '<a href="https://maps.google.com/maps/contrib/100197180373593920253">Cairo kitchen maadi</a>'],
                                                 'photo_reference': 'AUjq9jnkxxyWdA8GvP925M3iDsHvjzgbqCdBKzwdNC3HpioX602BktQqa047xAsZFEl__6RwH1SMZMjMJ8Axthlp9QF37hiSL1g5Bctb0Fr_HRI7d0AUBwEArUK2rbKna-IpDK_MwynnIpiTOXsQoQW9ChYzXjxNvSpFg5dEuZzh9CIHfEyl',
                                                 'width': 1440}], 'place_id': 'ChIJFZXQxcY5WBQRqJSpLOYYLOI',
                                     'plus_code': {'compound_code': 'X75G+WR Maadi, Egypt',
                                                   'global_code': '7GXHX75G+WR'}, 'rating': 4.5,
                                     'reference': 'ChIJFZXQxcY5WBQRqJSpLOYYLOI', 'scope': 'GOOGLE',
                                     'types': ['restaurant', 'food', 'point_of_interest', 'establishment'],
                                     'user_ratings_total': 15, 'vicinity': 'Street 231, Maadi'},
        {'business_status': 'OPERATIONAL',
         'geometry': {'location': {'lat': 29.95911529999999, 'lng': 31.2783709},
                      'viewport': {'northeast': {'lat': 29.9604639802915, 'lng': 31.2796946302915},
                                   'southwest': {'lat': 29.9577660197085, 'lng': 31.2769966697085}}},
         'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
         'icon_background_color': '#FF9E67',
         'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
         'name': 'Munch & Bagel', 'opening_hours': {'open_now': True},
         'place_id': 'ChIJRaLiNxM4WBQRhQsszG5EXmc', 'rating': 3, 'reference': 'ChIJRaLiNxM4WBQRhQsszG5EXmc',
         'scope': 'GOOGLE', 'types': ['restaurant', 'food', 'point_of_interest', 'establishment'],
         'user_ratings_total': 1, 'vicinity': '6 rd. 233, Maadi as Sarayat Al Gharbeyah, Maadi'},
        {'business_status': 'OPERATIONAL', 'geometry': {'location': {'lat': 29.959152, 'lng': 31.2778213},
                                                        'viewport': {'northeast': {'lat': 29.9605016302915,
                                                                                   'lng': 31.2790569302915},
                                                                     'southwest': {'lat': 29.9578036697085,
                                                                                   'lng': 31.2763589697085}}},
         'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
         'icon_background_color': '#FF9E67',
         'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
         'name': 'كازينو الحمام', 'opening_hours': {'open_now': True},
         'place_id': 'ChIJ69uLOhM4WBQRXX8n4-LOG68',
         'plus_code': {'compound_code': 'X75H+M4 Maadi, Egypt', 'global_code': '7GXHX75H+M4'}, 'rating': 4.6,
         'reference': 'ChIJ69uLOhM4WBQRXX8n4-LOG68', 'scope': 'GOOGLE',
         'types': ['restaurant', 'cafe', 'store', 'food', 'point_of_interest', 'establishment'],
         'user_ratings_total': 10, 'vicinity': '٣٥ شارع ٢٣٢, دجلة, Maadi'},
        {'business_status': 'OPERATIONAL', 'geometry': {'location': {'lat': 29.95912, 'lng': 31.2777017},
                                                        'viewport': {'northeast': {'lat': 29.9604692802915,
                                                                                   'lng': 31.2789969802915},
                                                                     'southwest': {'lat': 29.9577713197085,
                                                                                   'lng': 31.2762990197085}}},
         'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
         'icon_background_color': '#FF9E67',
         'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
         'name': 'CHEERA BITES , COFFEE & TALES', 'opening_hours': {'open_now': True}, 'photos': [
            {'height': 799, 'html_attributions': [
                '<a href="https://maps.google.com/maps/contrib/118119342535106085343">CHEERA BITES , COFFEE &amp; TALES</a>'],
             'photo_reference': 'AUjq9jknSeqNcRBT67TJyPj1wOBL--IsA4AimEGpQbQzmtUDZs1CNkNWRkjc-0pXSKOdiqL4E1DCxdGUNcvOu3uaIZ9qYg0VelvENSmxUR7kTbcQvHvu8ZaMEgVBhp0-aN2L8EhBOwRK8ZUY4-swl0EhhPDK5G6IBj3k5bpWQywQFMq49VRI',
             'width': 1599}], 'place_id': 'ChIJZydX7B05WBQRQ13Fc-uzs9U',
         'plus_code': {'compound_code': 'X75H+J3 Maadi, Egypt', 'global_code': '7GXHX75H+J3'}, 'rating': 5,
         'reference': 'ChIJZydX7B05WBQRQ13Fc-uzs9U', 'scope': 'GOOGLE',
         'types': ['restaurant', 'food', 'point_of_interest', 'establishment'], 'user_ratings_total': 8,
         'vicinity': '35 Street 232, دجلة, Maadi'}, {'business_status': 'OPERATIONAL', 'geometry': {
            'location': {'lat': 29.96073500000001, 'lng': 31.276757},
            'viewport': {'northeast': {'lat': 29.9620825302915, 'lng': 31.2781822802915},
                         'southwest': {'lat': 29.9593845697085, 'lng': 31.2754843197085}}},
                                                     'icon': 'https://maps.gstatic.com/mapfiles/place_api/icons/v1/png_71/restaurant-71.png',
                                                     'icon_background_color': '#FF9E67',
                                                     'icon_mask_base_uri': 'https://maps.gstatic.com/mapfiles/place_api/icons/v2/restaurant_pinlet',
                                                     'name': 'Al Dayaa', 'opening_hours': {'open_now': True},
                                                     'photos': [{'height': 1868, 'html_attributions': [
                                                         '<a href="https://maps.google.com/maps/contrib/111575701779837229586">Ahmed Abdallah</a>'],
                                                                 'photo_reference': 'AUjq9jn_tnx-yhTLNAZ8YrkD1qw0P_R_pAX0DkMCTNoxMz46gpL_zqBRSiIHFjd6JMbPHFUoQ3QVTMfWZGgsylBDSVaGQEnrrMDpZDPp4n6mDsCoiYW7J4WshzfmFetJaIYR6U5oGL3_XIbCHDJSyKwKi2--33wo-X0i3WKmp7zNSzZuIi4s',
                                                                 'width': 4000}],
                                                     'place_id': 'ChIJFyU4KG04WBQRpfqNCYmp1B8',
                                                     'plus_code': {'compound_code': 'X76G+7P Maadi, Egypt',
                                                                   'global_code': '7GXHX76G+7P'},
                                                     'price_level': 2, 'rating': 4.2,
                                                     'reference': 'ChIJFyU4KG04WBQRpfqNCYmp1B8',
                                                     'scope': 'GOOGLE',
                                                     'types': ['restaurant', 'food', 'point_of_interest',
                                                               'establishment'], 'user_ratings_total': 539,
                                                     'vicinity': '33 Street 231, Maadi'}]
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
                'cuisine': None,
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
        return_data.append(models.RestaurantSearch(
            place_id=restaurant_db["place_id"],
            name=restaurant_db["name"],
            address=place_data["vicinity"],
            coordinates=restaurant_db["location"]["coordinates"],
            image=get_place_photos(place_data["photos"][0]["photo_reference"]) if "photos" in place_data else None,
            cuisine=restaurant_db["cuisine"],
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

    return models.Restaurant(
        place_id=restaurant["place_id"],
        name=restaurant["name"],
        image=get_place_photos(place_data["photos"][0]["photo_reference"]) if "photos" in place_data else None,
        cuisine=restaurant["cuisine"],
        rating=place_data["rating"],
        description=place_data["editorial_summary"]['overview'] if 'editorial_summary' in place_data else None,
        gallery=[get_place_photos(photo["photo_reference"]) for photo in
                 place_data["photos"]] if "photos" in place_data else None,
        reviews=reviews,
        address=place_data["vicinity"],
        coordinates=restaurant["location"]["coordinates"],
        phone=place_data["formatted_phone_number"],
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
                'cuisine': cuisine if cuisine is not None else {'$exists': True},
                # add a search query if it exists
                'name': {'$regex': query, '$options': 'i'} if query is not None else {'$exists': True}
            }
        }
    ])
    return_data = []
    for restaurant_db in restaurants:
        place_data = get_place_details(restaurant_db["place_id"])['result']
        return_data.append(models.RestaurantSearch(
            place_id=restaurant_db["place_id"],
            name=restaurant_db["name"],
            address=place_data["vicinity"],
            coordinates=restaurant_db["location"]["coordinates"],
            image=get_place_photos(place_data["photos"][0]["photo_reference"]) if "photos" in place_data else None,
            cuisine=restaurant_db["cuisine"],
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
        place_data = get_place_details(restaurant_db["place_id"])['result']
        return_data.append(models.RestaurantSearch(
            place_id=restaurant_db["place_id"],
            name=restaurant_db["name"],
            address=place_data["vicinity"],
            coordinates=restaurant_db["location"]["coordinates"],
            image=get_place_photos(place_data["photos"][0]["photo_reference"]) if "photos" in place_data else None,
            cuisine=restaurant_db["cuisine"],
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
