import pymongo

client = pymongo.MongoClient(
    "mongodb+srv://dbUser:BLXNQYcB6S8QfB6v@cluster0.crrggdz.mongodb.net/?retryWrites=true&w=majority"
)
db = client.test