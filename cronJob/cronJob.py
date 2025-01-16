import psycopg2
import os
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables from your existing .env file
load_dotenv()

# Set up logging with more verbose output
logging.basicConfig(
    filename='report_checker.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Database configuration using your existing PG_ environment variables
DB_CONFIG = {
    'dbname': os.getenv('PG_DATABASE', 'postgres'),
    'user': os.getenv('PG_USERNAME', 'postgres'),
    'password': os.getenv('PG_PASSWORD'),
    'host': os.getenv('PG_HOSTNAME', '13.202.99.104'),  
    'port': os.getenv('PG_PORT', '5432')
}

# Constants
REPORT_THRESHOLD = 6  # Number of reports needed to quarantine a post

def connect_to_db():
    """Establish database connection"""
    try:
        # Log connection attempt
        logging.info(f"Attempting to connect to database at {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        logging.info(f"Database: {DB_CONFIG['dbname']}, User: {DB_CONFIG['user']}")
        
        conn = psycopg2.connect(
            dbname=DB_CONFIG['dbname'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port']
        )
        
        logging.info("Database connection successful")
        return conn
    except Exception as e:
        logging.error(f"Database connection failed: {str(e)}")
        raise

def check_reported_posts():
    """Check for posts that exceed the report threshold and quarantine them"""
    conn = None
    cur = None
    try:
        conn = connect_to_db()
        cur = conn.cursor()

        # First, ensure the quarantined column exists
        try:
            cur.execute("""
                ALTER TABLE content 
                ADD COLUMN IF NOT EXISTS quarantined BOOLEAN DEFAULT FALSE;
            """)
            conn.commit()
            logging.info("Ensured quarantined column exists in content table")
        except Exception as e:
            logging.error(f"Error ensuring quarantined column: {str(e)}")
            conn.rollback()
            raise

        # Find and quarantine posts with report counts exceeding threshold
        query = """
        WITH report_counts AS (
            SELECT 
                contentid,
                COUNT(*) as report_count
            FROM reports
            WHERE contentid IS NOT NULL
            GROUP BY contentid
            HAVING COUNT(*) >= %s
        )
        UPDATE content c
        SET quarantined = TRUE
        FROM report_counts rc
        WHERE c.contentid = rc.contentid 
        AND c.quarantined = FALSE
        RETURNING c.contentid, rc.report_count;
        """

        cur.execute(query, (REPORT_THRESHOLD,))
        quarantined_posts = cur.fetchall()

        # Log the quarantined posts
        for post_id, report_count in quarantined_posts:
            logging.info(f"Quarantined post {post_id} with {report_count} reports")

        conn.commit()
        
        # Log summary
        if quarantined_posts:
            logging.info(f"Quarantined {len(quarantined_posts)} posts")
        else:
            logging.info("No posts needed quarantine")

        # Optional: Log some statistics
        cur.execute("""
            SELECT 
                COUNT(*) as total_posts,
                SUM(CASE WHEN quarantined THEN 1 ELSE 0 END) as quarantined_posts
            FROM content;
        """)
        stats = cur.fetchone()
        logging.info(f"Current stats - Total posts: {stats[0]}, Quarantined: {stats[1]}")

    except Exception as e:
        logging.error(f"Error in check_reported_posts: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def main():
    """Main function to run the report checker"""
    script_start_time = datetime.now()
    logging.info(f"Starting report checker cron job at {script_start_time}")
    

    logging.info(f"Using database host: {DB_CONFIG['host']}")
    logging.info(f"Using database port: {DB_CONFIG['port']}")
    logging.info(f"Using database name: {DB_CONFIG['dbname']}")
    logging.info(f"Using database user: {DB_CONFIG['user']}")
    
    try:
        check_reported_posts()
        script_end_time = datetime.now()
        execution_time = (script_end_time - script_start_time).total_seconds()
        logging.info(f"Report checker completed successfully. Execution time: {execution_time} seconds")
    except Exception as e:
        logging.error(f"Report checker failed: {str(e)}")

if __name__ == "__main__":
    main()