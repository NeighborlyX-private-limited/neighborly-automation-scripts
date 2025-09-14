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
    
    async def get_custom_insights_by_location(self, location_slug: str) -> List[Dict]:
        """Fetch existing custom insights for the location from insights table"""
        await self.init_db()
        
        async with self.pg_pool.acquire() as conn:
            # Query the insights table for user-generated insights
            query = """
            SELECT i.id, i.location_slug, i.title, i.summary, i.cheers, i.boos, 
                   i.status_tag, i.source_type, i.created_at, i.updated_at,
                   ic.slug as category_slug, ic.name as category_name
            FROM insights i
            JOIN insight_categories ic ON i.category_id = ic.id
            WHERE i.location_slug = $1 AND i.source_type = 'user'
            ORDER BY i.created_at DESC
            LIMIT 100
            """
            
            rows = await conn.fetch(query, location_slug)
            
            return [
                {
                    "id": str(row['id']),
                    "location_slug": row['location_slug'],
                    "title": row['title'],
                    "summary": row['summary'],
                    "cheers": row['cheers'],
                    "boos": row['boos'],
                    "status_tag": row['status_tag'],
                    "source_type": row['source_type'],
                    "created_at": row['created_at'],
                    "updated_at": row['updated_at'],
                    "category_slug": row['category_slug'],
                    "category_name": row['category_name']
                } for row in rows
            ]
    
    async def get_nearby_custom_insights(self, lat: float, lon: float, radius: int = 5000) -> List[Dict]:
        """Fetch custom insights within radius of coordinates from insights table"""
        await self.init_db()
        
        async with self.pg_pool.acquire() as conn:
            # Get insights from nearby locations using location_summaries geometry
            query = """
            SELECT DISTINCT i.id, i.location_slug, i.title, i.summary, i.cheers, i.boos, 
                   i.status_tag, i.source_type, i.created_at, i.updated_at,
                   ic.slug as category_slug, ic.name as category_name,
                   ST_X(ls.geom) as lon, ST_Y(ls.geom) as lat
            FROM insights i
            JOIN insight_categories ic ON i.category_id = ic.id
            JOIN location_summaries ls ON i.location_slug = ls.location_slug
            WHERE ST_DWithin(
                ls.geom,
                ST_SetSRID(ST_Point($1, $2), 4326),
                $3
            ) AND i.source_type = 'user'
            ORDER BY i.created_at DESC
            LIMIT 50
            """
            
            rows = await conn.fetch(query, lon, lat, radius)
            
            return [
                {
                    "id": str(row['id']),
                    "location_slug": row['location_slug'],
                    "title": row['title'],
                    "summary": row['summary'],
                    "cheers": row['cheers'],
                    "boos": row['boos'],
                    "status_tag": row['status_tag'],
                    "source_type": row['source_type'],
                    "created_at": row['created_at'],
                    "updated_at": row['updated_at'],
                    "category_slug": row['category_slug'],
                    "category_name": row['category_name'],
                    "lat": row['lat'],
                    "lon": row['lon']
                } for row in rows
            ]
    
    async def close(self):
        """Close database connections"""
        if self.pg_pool:
            await self.pg_pool.close()
