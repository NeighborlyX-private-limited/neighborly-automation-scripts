import psycopg2

# helper functions
def checkEnvVariable(hostname = None, username = None, password = None, database= None, port = None) -> bool:
    return not (hostname == None  or username == None or  password == None or database == None or port == None)


def connect2Postgres(hostname, username, password, database, port):
    print("Trying to connect to database.")
    try :
        connection = psycopg2.connect(
            host=hostname,
            port=port,
            database=database,
            user=username,
            password=password
        )
        print("Database connected")
        return connection
    
    except Exception as e:
        print("Error while connecting to postgreSQL. ", e)
        return e
    

def emptyTrendingPostsTable(cursor):
    try:
        query = '''TRUNCATE TABLE trending_posts'''
        cursor.execute(query)
    
    except Exception as e:
        print("Error occured while deleting entries in trending_posts table.")
        return e
    

def fetchLast48HourPosts(cursor):
    try:
        query = '''
            SELECT contentid, type as postType, cheers, boos, city, ROUND(EXTRACT(EPOCH FROM (NOW() - createdat)) / 43200, 2) AS tdf
            FROM content 
            WHERE 
            createdat >= NOW() - INTERVAL '48 hours' AND city IS NOT NULL AND quarantined = FALSE;
            '''
        cursor.execute(query)
        posts = cursor.fetchall()
        return posts
    
    except Exception as e:
        print("Error while fetching posts.")
        return e
    

def getCommentCount(cursor, contentid):
    try:
        query = f''' 
            SELECT COUNT(*) 
            FROM comments 
            WHERE contentid = {contentid};
            '''
        cursor.execute(query)
        commentCount = cursor.fetchone()[0]
        return commentCount
    
    except Exception as e:
        print("Error occured while fetching comments.")
        return e


def getReportCount(cursor, contentid):
    try:
        query = f''' 
            SELECT COUNT(*) 
            FROM reports 
            WHERE contentid = {contentid};
            '''
        cursor.execute(query)
        reportCount = cursor.fetchone()[0]
        return reportCount
    
    except Exception as e:
        print("Error occured while fetching comments.")
        return e
    

def addTrendingPost(connection, cursor, contentid, posType, city, score):
    try:
        query = '''
                INSERT INTO trending_posts (contentid, type, city, score) 
                VALUES (%s, %s, %s, %s);
                '''
        cursor.execute(query, (contentid, posType, city, score))
        connection.commit()
    
    except Exception as e:
        print("Error while adding post to trending_posts table")
        return e