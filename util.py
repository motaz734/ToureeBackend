from db_conn import db
import requests
import urllib.parse

def get_cuisine(name:str):
    url = f"https://www.elmenus.com:443/2.0/restaurant/autocomplete?q={urllib.parse.quote(name)}&city=35185821-2224-11e8-924e-0242ac110011"
    headers = {
        "Sec-Ch-Ua": "\"Not:A-Brand\";v=\"99\", \"Chromium\";v=\"112\"",
        "Sec-Ch-Ua-Mobile": "?0",
        "Client-Version": "5",
        "Authorization": "Bearer eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJlbG1lbnVzLmNvbSIsInN1YiI6ImJlMDZlOGQ1LTc0ZDUtNDI1Ny1"
                         "iOTg2LTczYjU4ODk5MDAxOSIsImp0aSI6IlZxVm04aHRtRlVwV2daRzJ2UlU0M1EiLCJpYXQiOjE2ODI1MTY0MTYsIm"
                         "5iZiI6MTY4MjUxNjI5NiwiaXNHdWVzdCI6dHJ1ZSwiZGV2aWNlIjoiNWk1bzYxbGd4cXR6NzUiLCJ2ZXJzaW9uIjoxL"
                         "jB9.Hj8XYGoSvR53wJG7D0zwQCThDQY8w4eTBfR6X-yD1oPhQcOvaOcR5JvfU79J1KTF2DYLdDROlyYtc_tWEmOwWQ",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                      " Chrome/112.0.5615.50 Safari/537.36",
        "Accept": "application/json",
        "Lang": "EN",
        "Device-Model": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                        " Chrome/112.0.5615.50 Safari/537.36",
        "Client-Model": "WEB", "X-Device-Id": "5i5o61lgxqtz75",
        "Sec-Ch-Ua-Platform": "\"Windows\"",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://www.elmenus.com/",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "close"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        response = response.json()
        for restaurant in response["data"]:
            if restaurant['data']['name'].lower() == name.lower() or restaurant['data']['name'].replace(" ", "").lower() == name.replace(" ", "").lower():
                logo = restaurant['data']["logo"].replace("{{PHOTO_VERSION}}", "Normal").replace("{{PHOTO_EXTENSION}}", "jpg")
                cuisines = {
                    tag['data']['name']: tag['data']['photoUrl'].replace("{{PHOTO_VERSION}}", "Normal").replace("{{PHOTO_EXTENSION}}", "jpg")
                    for tag in restaurant['data']['tags']
                }
                return cuisines

def get_restaurants():
    # find all restaurants with cuisine empty array
    restaurants = db.Restaurants.find({"cuisine": []})
    for restaurant in restaurants:
        cuisines = get_cuisine(restaurant["name"])
        print(f"Restaurant: {restaurant['name']}")
        print(f"Cuisines: {cuisines}")
        print("=====================================")
        if cuisines:
            db.Restaurants.update_one({"_id": restaurant["_id"]}, {"$set": {"cuisine": {k: v for k, v in cuisines.items()}}})
    print("Done")

def get_restaurants_by_cuisine(cuisine:str):
    restaurants = db.Restaurants.aggregate([
        {"$match": {f"cuisine.{cuisine}": {"$exists": True}}},
    ])
    for restaurant in restaurants:
        print(restaurant["name"])
        print(restaurant["cuisine"])
        print("=====================================")


if __name__ == '__main__':
    get_restaurants()
