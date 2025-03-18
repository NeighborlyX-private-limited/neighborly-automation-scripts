# essential imports
from dotenv import load_dotenv
from utils import checkEnvVariable, connect2Postgres, fetchLast48HourPosts, getCommentCount, getReportCount, emptyTrendingPostsTable, addTrendingPost
import os

# load env 
load_dotenv()

# get relevant env variables
hostname = os.getenv("PG_HOSTNAME") if os.getenv("PG_HOSTNAME") else None
username = os.getenv("PG_USERNAME") if os.getenv("PG_USERNAME") else None
password = os.getenv("PG_PASSWORD") if os.getenv("PG_PASSWORD") else None
database = os.getenv("PG_DATABASE") if os.getenv("PG_DATABASE") else None
port = os.getenv("PG_PORT") if os.getenv("PG_PORT") else None

# check env variable loaded successfully
isLoaded = checkEnvVariable(
    hostname = hostname, 
    username = username, 
    password = password, 
    database = database, 
    port = port
    )

if isLoaded == False:
    print("All or some environment variables loaded are None")
    print("hostname = ",hostname)
    print("username = ",username)
    print("password = ",password)
    print("database = ",database)
    print("port = ",port)

else :   
# connect postgres database
    try:
        connection = connect2Postgres(
            hostname=hostname, 
            username=username, 
            password=password, 
            database=database, 
            port=port
            )
        
        cursor = connection.cursor()

        #clear trending posts table
        emptyTrendingPostsTable(cursor = cursor)
        # fetch last 48 hours posts
        posts = fetchLast48HourPosts(cursor)
        for contentid, postType, cheers, boos, city, tdf in posts:
            commentCount = getCommentCount(cursor = cursor, contentid = contentid)
            reportCount = getReportCount(cursor = cursor, contentid = contentid)
            
            # calculate score
            score = (5 * commentCount) + (3 * cheers) - (3 * boos) - (5 * reportCount) - tdf
            print("score = ",score)

            # store trending post per city
            addTrendingPost(connection = connection, cursor = cursor, contentid = contentid, posType = postType, city = city, score = score)

    except Exception as e :
        print(e)
    