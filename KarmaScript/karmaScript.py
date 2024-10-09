import pymongo
import random
from bson.objectid import ObjectId
import psycopg2

import yaml

# Load YAML file
with open('./config/config.yml', 'r') as file:
    config = yaml.safe_load(file)

DB_URL = config['database']['url']
DB_NAME = config['database']['name']
DB_COLLECTION = config['database']['collection']
PG_HOST = config['database']['pgHost']
PG_PORT = config['database']['pgPort']
PG_DB = config['database']['pgDB']
PG_USER = config['database']['pgUser']
PG_PASSWORD = config['database']['pgPassword']
CONTENTS = config['database']['contents']
CONTENT_VOTES = config['database']['contentVotes']
COMMENTS = config['database']['comments']
COMMENT_VOTES = config['database']['commentVotes']

# Connect to the MongoDB server
client = pymongo.MongoClient(DB_URL)

# Access a specific database
db = client[DB_NAME]

# Access a specific collection
collection = db[DB_COLLECTION]

# Connect to PostgreSQL database
conn = psycopg2.connect(
    host=PG_HOST,
    port=PG_PORT,
    database=PG_DB,
    user=PG_USER,
    password=PG_PASSWORD
)

# Create a cursor object
cursor = conn.cursor()

cursor.execute(f"SELECT voteid, contentid, votetype FROM {CONTENT_VOTES} WHERE processed=false;")
rows = cursor.fetchall()
for row in rows:
    cursor.execute(f"SELECT userid FROM {CONTENTS} WHERE contentid = %s;", (row[1],))
    userId = cursor.fetchone()
    cursor.execute(
    f"""
    UPDATE {CONTENT_VOTES}
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

cursor.execute(f"SELECT voteid, commentid, votetype FROM {COMMENT_VOTES} WHERE processed=false;")
comment_rows = cursor.fetchall()
for row in comment_rows:
    cursor.execute(f"SELECT userid FROM {COMMENTS} WHERE commentid = %s;", (row[1],))
    userId = cursor.fetchone()
    cursor.execute(
        f"""
    UPDATE {COMMENT_VOTES}
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
