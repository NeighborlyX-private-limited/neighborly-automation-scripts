import yaml
import pymongo
import requests

# Load YAML file
with open('./config/config.yml', 'r') as file:
    config = yaml.safe_load(file)

authToken = input("Please provide your token: ")
username = input("Please enter username to whom you want to ban: ")

dbUrl = config['database']['url']
dbName = config['database']['name']
dbCollection = config['database']['collection']

# Connect to the MongoDB server
client = pymongo.MongoClient(dbUrl)

# Access a specific database
db = client[dbName]

# Access a specific collection (similar to a table in SQL)
collection = db[dbCollection]

uri = config['API']['uri']

headers = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "authorization": "Bearer"+authToken
}

user = collection.find_one({"username": username})

if user is None:
    print("No such username exist")

else :
    payload = {
        "token": user.fcmToken,
        "eventType": "User Trigger",
        "userid": user._id,
        "title": "Your id is banned",
        "content": "We are banning you for wrong or invalid content",
        "notificationBody": "You are banned for wrong or bad content",
        "notificationTitle": "You are banned"
    }
    # Make the POST request
    response = requests.post(uri, json=payload, headers=headers)
    # Check the response status and handle the response data
    if response.status_code == 200:
    # Parse JSON response data
        data = response.json()
        print(data)
    else:
        print(f"Failed to post data. Status code: {response.status_code}")
