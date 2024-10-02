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

cursor.execute(f"SELECT voteid, contentid, votetype FROM {contentVotes} WHERE processed=false;")
rows = cursor.fetchall()
for row in rows:
    cursor.execute(f"SELECT userid FROM {contents} WHERE contentid = %s;", (row[1],))
    userId = cursor.fetchone()
    cursor.execute(
    f"""
    UPDATE {contentVotes}
    SET processed = true
    WHERE voteid = %s
    """,
        (row[0],)
    )
    conn.commit()
    if row[2] == 'cheer':
        collection.update_one(
            {"_id": ObjectId(userId[0])},
            {"$inc": {"karma": 1}}
        )
    elif row[2] == 'boo':
        collection.update_one(
            {"_id": ObjectId(userId[0])},
            {"$inc": {"karma": -1}}
        )

cursor.execute(f"SELECT voteid, commentid, votetype FROM {commentVotes} WHERE processed=false;")
comment_rows = cursor.fetchall()
for row in comment_rows:
    cursor.execute(f"SELECT userid FROM {comments} WHERE commentid = %s;", (row[1],))
    userId = cursor.fetchone()
    cursor.execute(
        f"""
    UPDATE {commentVotes}
    SET processed = true
    WHERE voteid = %s
    """,
        (row[0],)
    )
    conn.commit()
    if row[2] == 'cheer':
        collection.update_one(
            {"_id": ObjectId(userId[0])},
            {"$inc": {"karma": 1}}
        )
    elif row[2] == 'boo':
        collection.update_one(
            {"_id": ObjectId(userId[0])},
            {"$inc": {"karma": -1}}
        )
