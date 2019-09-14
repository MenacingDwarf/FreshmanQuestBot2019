from pymongo import MongoClient
db = MongoClient()['am-cp']

while True:
    group = {
        'id': int(input('Номер: ')),
        'stations': [],
        'current_station': 0,
        'experience': 0,
        'money': 0,
    }
    db['groups'].insert_one(group)
