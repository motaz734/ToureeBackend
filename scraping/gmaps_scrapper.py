from pprint import pprint

from geopy.distance import geodesic

from config import Config
from PIL import Image
import googlemaps

gmaps = googlemaps.Client(key=Config.GMAPS_KEY)


def get_nearby_places(lat, lng, type='restaurant'):
    places = gmaps.places_nearby(
        location=(lat, lng),
        open_now=True,
        rank_by='distance',
        type=type
    )
    return places

def get_country(lat, lng):
    country = gmaps.reverse_geocode(
        latlng=(lat, lng),
        result_type='country'
    )
    return country[0]['address_components'][0]['short_name'].lower()

def get_popular_places(lat,lng, type='tourist_attraction'):
    places = gmaps.places(
        type=type,
        query='Things to do',
        region=get_country(lat, lng),
    )
    return places


def get_place_details(place_id):
    place = gmaps.place(place_id=place_id)
    return place


def get_place_photos(ref, max_width=400, max_height=400):
    photo = f"https://maps.googleapis.com/maps/api/place/photo" \
            f"?maxwidth={max_width}" \
            f"&maxheight={max_height}" \
            f"&photo_reference={ref}" \
            f"&key={Config.GMAPS_KEY}"
    return photo


if __name__ == '__main__':
    places = get_popular_places(29.960344, 31.278265)
    # print name and distance
    for place in places['results']:
        distance = geodesic((29.960344, 31.278265), (place['geometry']['location']['lat'], place['geometry']['location']['lng'])).km
        print(f"{place['name']} - {distance} km - {place['rating']}")

