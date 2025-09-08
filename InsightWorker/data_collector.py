# insights_worker/data_collector.py
import asyncpg
import asyncio
from typing import List, Dict, Optional
from config import Config

class DataCollector:
    def __init__(self):
        self.config = Config()
        self.pg_pool = None
    
    async def init_db(self):
        """Initialize database connection pool"""
        if not self.pg_pool:
            self.pg_pool = await asyncpg.create_pool(
                host=self.config.PG_HOST,
                port=self.config.PG_PORT,
                user=self.config.PG_USER,
                password=self.config.PG_PASSWORD,
                database=self.config.PG_DATABASE,
                min_size=1,
                max_size=5
            )
    
    async def get_location_info(self, location_slug: str) -> Optional[Dict]:
        """Get location coordinates from database"""
        await self.init_db()
        
        async with self.pg_pool.acquire() as conn:
            # Try to get from existing location_summaries first
            result = await conn.fetchrow(
                "SELECT ST_X(geom) as lon, ST_Y(geom) as lat FROM location_summaries WHERE location_slug = $1",
                location_slug
            )
            
            if result:
                return {"lat": result['lat'], "lon": result['lon']}
            
            # If not found, we'll need to parse from slug or get from posts
            # For now, return None and handle in main.py
            return None
    
    async def get_nearby_posts(self, lat: float, lon: float, radius: int = 5000) -> List[Dict]:
        """Fetch posts within radius of coordinates"""
        await self.init_db()
        
        async with self.pg_pool.acquire() as conn:
            # Use the same ST_DWithin query as your wallController
            query = """
            SELECT contentid, userid, username, title, body, createdat, cheers, boos, 
                   type, city, ST_X(postlocation) as lon, ST_Y(postlocation) as lat
            FROM content 
            WHERE ST_DWithin(
                postlocation,
                ST_SetSRID(ST_Point($1, $2), 4326),
                $3
            ) AND quarantined = false
            ORDER BY createdat DESC
            LIMIT 200
            """
            
            rows = await conn.fetch(query, lon, lat, radius)
            
            return [
                {
                    "contentid": row['contentid'],
                    "userid": row['userid'],
                    "username": row['username'],
                    "title": row['title'],
                    "body": row['body'],
                    "createdat": row['createdat'],
                    "cheers": row['cheers'],
                    "boos": row['boos'],
                    "type": row['type'],
                    "city": row['city'],
                    "lat": row['lat'],
                    "lon": row['lon']
                } for row in rows
            ]
    
    async def get_comments_for_posts(self, posts: List[Dict]) -> List[Dict]:
        """Get comments for the collected posts"""
        if not posts:
            return []
            
        await self.init_db()
        post_ids = [post['contentid'] for post in posts]
        
        async with self.pg_pool.acquire() as conn:
            query = """
            SELECT commentid, contentid, userid, username, body, createdat, cheers, boos
            FROM comments 
            WHERE contentid = ANY($1)
            ORDER BY createdat DESC
            LIMIT 500
            """
            
            rows = await conn.fetch(query, post_ids)
            
            return [
                {
                    "commentid": row['commentid'],
                    "contentid": row['contentid'],
                    "userid": row['userid'],
                    "username": row['username'],
                    "body": row['body'],
                    "createdat": row['createdat'],
                    "cheers": row['cheers'],
                    "boos": row['boos']
                } for row in rows
            ]
    
    async def close(self):
        """Close database connections"""
        if self.pg_pool:
            await self.pg_pool.close()
