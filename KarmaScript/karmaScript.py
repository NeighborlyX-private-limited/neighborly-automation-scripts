import pymongo
import random
from bson.objectid import ObjectId
import psycopg2
import yaml

# Load YAML file
with open('./config/config.yml', 'r') as file:
    config = yaml.safe_load(file)

dbUrl = config['database']['url']
dbName = config['database']['name']
dbCollection = config['database']['collection']
pgHost = config['database']['pgHost']
pgPort = config['database']['pgPort']
pgDB = config['database']['pgDB']
pgUser = config['database']['pgUser']
pgPassword = config['database']['pgPassword']
contents = config['database']['contents']
contentVotes = config['database']['contentVotes']
comments = config['database']['comments']
commentVotes = config['database']['commentVotes']

# Connect to the MongoDB server
client = pymongo.MongoClient(dbUrl)

# Access a specific database
db = client[dbName]

# Access a specific collection
collection = db[dbCollection]

# Connect to PostgreSQL database
conn = psycopg2.connect(
    host=pgHost,
    port=pgPort,
    database=pgDB,
    user=pgUser,
    password=pgPassword
)

# Create a cursor object
cursor = conn.cursor()

# Process content votes
cursor.execute(f"SELECT voteid, contentid, votetype FROM {contentVotes} WHERE processed=false;")
rows = cursor.fetchall()

for row in rows:
    cursor.execute(f"SELECT userid FROM {contents} WHERE contentid = %s;", (row[1],))
    userId = cursor.fetchone()
    
    # Check if userId is missing
    if userId is None or userId[0] is None:
        print(f"User ID is missing for contentid {row[1]}. Skipping update.")
        continue  # Skip this vote if no user is found
    
    # Update processed status in PostgreSQL
    cursor.execute(
        f"""
        UPDATE {contentVotes}
        SET processed = true
        WHERE voteid = %s
        """,
        (row[0],)
    )
    conn.commit()
    
    # Attempt to update the user's karma in MongoDB
    try:
        update_result = collection.update_one(
            {"_id": ObjectId(userId[0])},
            {"$inc": {"karma": 1 if row[2] == 'cheer' else -1}}
        )
        
        if update_result.matched_count == 0:
            print(f"User with ID {userId[0]} not found in MongoDB. Skipping karma update.")
    
    except Exception as e:
        print(f"Failed to update karma for user {userId[0]}: {e}")

# Process comment votes
cursor.execute(f"SELECT voteid, commentid, votetype FROM {commentVotes} WHERE processed=false;")
comment_rows = cursor.fetchall()

for row in comment_rows:
    cursor.execute(f"SELECT userid FROM {comments} WHERE commentid = %s;", (row[1],))
    userId = cursor.fetchone()
    
    # Check if userId is missing
    if userId is None or userId[0] is None:
        print(f"User ID is missing for commentid {row[1]}. Skipping update.")
        continue  # Skip this vote if no user is found
    
    # Update processed status in PostgreSQL
    cursor.execute(
        f"""
        UPDATE {commentVotes}
        SET processed = true
        WHERE voteid = %s
        """,
        (row[0],)
    )
    conn.commit()
    
    # Attempt to update the user's karma in MongoDB
    try:
        update_result = collection.update_one(
            {"_id": ObjectId(userId[0])},
            {"$inc": {"karma": 1 if row[2] == 'cheer' else -1}}
        )
        
        if update_result.matched_count == 0:
            print(f"User with ID {userId[0]} not found in MongoDB. Skipping karma update.")
    
    except Exception as e:
        print(f"Failed to update karma for user {userId[0]}: {e}")
