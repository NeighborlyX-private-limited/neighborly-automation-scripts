import psycopg2
import os
import schedule
import time
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    filename='report_checker.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Database configuration
DB_CONFIG = {
    'dbname': os.getenv('PG_DATABASE', 'postgres'),
    'user': os.getenv('PG_USERNAME', 'postgres'),
    'password': os.getenv('PG_PASSWORD'),
    'host': os.getenv('PG_HOSTNAME', 'localhost'),
    'port': os.getenv('PG_PORT', '5432')
}

# Report threshold
REPORT_THRESHOLD = 6

def connect_to_db():

    try:
        logging.info("Connecting to the database...")
        conn = psycopg2.connect(
            dbname=DB_CONFIG['dbname'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port']
        )
        logging.info("Database connection successful.")
        return conn
    except Exception as e:
        logging.error(f"Database connection failed: {str(e)}")
        raise

def check_reported_posts():
    conn = None
    cur = None
    try:
        conn = connect_to_db()
        cur = conn.cursor()

        # Ensure the quarantined column exists in the content table
        cur.execute("""
            ALTER TABLE content 
            ADD COLUMN IF NOT EXISTS quarantined BOOLEAN DEFAULT FALSE;
        """)
        conn.commit()
        logging.info("Ensured 'quarantined' column exists in content table.")

        # Quarantine logic: Handle posts with unprocessed reports >= threshold
        query = """
        WITH report_counts AS (
            SELECT 
                contentid,
                COUNT(*) AS new_report_count
            FROM reports
            WHERE contentid IS NOT NULL
              AND processed = FALSE -- Only count unprocessed reports
            GROUP BY contentid
            HAVING COUNT(*) >= %s -- Report threshold
        )
        UPDATE content c
        SET quarantined = TRUE
        FROM report_counts rc
        WHERE c.contentid = rc.contentid 
          AND c.quarantined = FALSE -- Only quarantine posts not already quarantined
        RETURNING c.contentid, rc.new_report_count;
        """

        cur.execute(query, (REPORT_THRESHOLD,))
        quarantined_posts = cur.fetchall()

        # Log quarantined posts
        for post_id, report_count in quarantined_posts:
            logging.info(f"Quarantined post {post_id} with {report_count} new reports.")

        conn.commit()

        # Log total quarantined posts summary
        if quarantined_posts:
            logging.info(f"Quarantined {len(quarantined_posts)} posts in this run.")
        else:
            logging.info("No posts needed quarantine.")

        # Log current statistics
        cur.execute("""
            SELECT 
                COUNT(*) AS total_posts,
                SUM(CASE WHEN quarantined THEN 1 ELSE 0 END) AS quarantined_posts
            FROM content;
        """)
        stats = cur.fetchone()
        logging.info(f"Stats - Total posts: {stats[0]}, Quarantined: {stats[1]}")

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

def process_moderation_action(content_id, action="unquarantine"):
    conn = None
    cur = None
    try:
        conn = connect_to_db()
        cur = conn.cursor()

        if action == "unquarantine":
            # Mark all reports as processed
            cur.execute("""
                UPDATE reports
                SET processed = TRUE
                WHERE contentid = %s;
            """, (content_id,))
            conn.commit()
            logging.info(f"Marked all reports for post {content_id} as processed.")

            # Unquarantine the post
            cur.execute("""
                UPDATE content
                SET quarantined = FALSE
                WHERE contentid = %s;
            """, (content_id,))
            conn.commit()
            logging.info(f"Post {content_id} has been unquarantined by moderators.")

    except Exception as e:
        logging.error(f"Error in moderation action for post {content_id}: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def run_report_checker():

    script_start_time = datetime.now()
    logging.info(f"Scheduled report checker starting at {script_start_time}")

    try:
        check_reported_posts()
        script_end_time = datetime.now()
        execution_time = (script_end_time - script_start_time).total_seconds()
        logging.info(f"Scheduled report checker completed in {execution_time:.2f} seconds.")
    except Exception as e:
        logging.error(f"Scheduled report checker failed: {str(e)}")

def main():
   
    schedule.every(1).hour.do(run_report_checker)
    
    logging.info("Scheduler initialized. Waiting for scheduled tasks...")
    
  
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()