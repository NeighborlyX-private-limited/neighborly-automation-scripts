import yaml
import pymongo
import requests
import sys

# Load YAML file
with open('./config/config.yml', 'r') as file:
    config = yaml.safe_load(file)

authToken = sys.argv[1]
username = sys.argv[2]

DB_URL = config['database']['url']
DB_NAME = config['database']['name']
DB_COLLECTION = config['database']['collection']
URI = config['API']['uri']

# Connect to the MongoDB server
client = pymongo.MongoClient(DB_URL)

# Access a specific database
db = client[DB_NAME]

# Access a specific collection (similar to a table in SQL)
collection = db[DB_COLLECTION]



headers = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "authorization": "Bearer "+authToken
}

user = collection.find_one({"username": username})

if user is None:
    print("No such username exist")

else :
    collection.update_one(
        {"_id": user['_id']},
        {"$set": {"isBanned": True}}
    )
    try:
        payload = {
            "userId": str(user['_id']),
            "title": "Rule-Breaking? Not Cool!",
            "content": "Hey, we love your enthusiasm, but not your recent posts. You're banned for rule-breaking. Let’s keep it clean next time!"
        }
        # Make the POST request
        response = requests.post(URI, json=payload, headers=headers)
        # Check the response status and handle the response data
        if response.status_code == 200:
            # Parse JSON response data
            data = response.json()
            print(data)
            print("userId: "+str(user['_id'])+" is banned")
        else:
            print(f"Failed to post data. Status code: {response.status_code}")
    except:
        print("Updated the Database but not able to send notification!")
