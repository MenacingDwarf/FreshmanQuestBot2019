import json

from pymongo import MongoClient

db = MongoClient()['am-cp']

with open('db.json', 'r', encoding='UTF-8') as file:
    stations = json.loads(file.read())["stations"]
    db['stations'].insert_many(stations)
