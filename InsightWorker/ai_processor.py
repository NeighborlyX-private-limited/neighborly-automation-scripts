import openai
import json
import logging
import asyncio
import aiohttp
import ssl, certifi
from typing import List, Dict, Optional
from config import Config
import re
from datetime import datetime, timedelta
import urllib.parse
from constants import (
    CategoryType, SourceType, StatusTag,
    CATEGORY_DEFINITIONS, REDDIT_QUERIES, GOOGLE_PLACES_QUERIES,
    REDDIT_CONFIG, GOOGLE_PLACES_CONFIG, OPENAI_CONFIG, TEXT_CONFIG,
    RELEVANCE_KEYWORDS, REQUIRED_CATEGORIES, SYSTEM_PROMPTS,
    JSON_RESPONSE_TEMPLATE, ERROR_MESSAGES, DEBUG_LABELS
)

logger = logging.getLogger(__name__)


class AIProcessor:
    def __init__(self):
        self.config = Config()
        openai.api_key = self.config.OPENAI_API_KEY
        
        # Use constants for categories and queries
        self.categories = CATEGORY_DEFINITIONS
        self.reddit_queries = REDDIT_QUERIES
    
    async def generate_insights(self, location_slug: str, lat: float, lon: float) -> Optional[Dict]:
        try:
            logger.info(f"Starting AI insight generation for {location_slug}")
            
            # Step 1: Get Google Places data for the area
            places_data = await self._fetch_google_places_data(lat, lon)
            
            # Step 2: Get Reddit data for the location
            reddit_data = await self._fetch_reddit_data(location_slug)
            
            # Step 3: Create comprehensive prompt with location data
            prompt = self._build_comprehensive_prompt(location_slug, places_data, reddit_data, lat, lon)
            
            # Step 4: Call OpenAI with rich context
            response = await self._call_openai(prompt)
            
            if response:
                return self._parse_ai_response(response)
            
            return None
            
        except Exception as e:
            logger.error(f"AI processing error: {str(e)}")
            return None
    
    async def _fetch_reddit_data(self, location_slug: str) -> Dict:
        """Fetch relevant Reddit posts and comments for the location"""
        reddit_data = {category.value: [] for category in CategoryType}
        
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            async with aiohttp.ClientSession() as session:
                # Set headers to mimic a browser request
                headers = {
                    'User-Agent': REDDIT_CONFIG['USER_AGENT']
                }
                
                tasks = []
                for category, queries in self.reddit_queries.items():
                    for query in queries:
                        # Create search query combining location and topic
                        search_query = f"{location_slug} {query}"
                        task = self._search_reddit(session, search_query, category, headers, ssl_context)
                        tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results and categorize
                for result in results:
                    if not isinstance(result, Exception) and result:
                        category, posts = result
                        reddit_data[category].extend(posts)
                        
        except Exception as e:
            logger.error(f"Error fetching Reddit data: {e}")
        
        return reddit_data
    
    async def _search_reddit(self, session, query: str, category: str, headers: Dict, ssl_context) -> Optional[tuple]:
        """Search Reddit for specific query and category"""
        try:
            # Use Reddit's JSON API
            encoded_query = urllib.parse.quote(query)
            url = f"{REDDIT_CONFIG['BASE_URL']}?q={encoded_query}&sort={REDDIT_CONFIG['SORT']}&t={REDDIT_CONFIG['TIME_FILTER']}&limit={REDDIT_CONFIG['LIMIT']}"
            
            async with session.get(url, headers=headers, ssl=ssl_context) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    posts = []
                    for post in data.get("data", {}).get("children", []):
                        post_data = post.get("data", {})
                        
                        # Filter for relevance and quality
                        if (post_data.get("score", 0) > REDDIT_CONFIG["MIN_SCORE"] and 
                            post_data.get("num_comments", 0) > REDDIT_CONFIG["MIN_COMMENTS"]):
                            
                            post_info = {
                                "title": post_data.get("title", ""),
                                "selftext": post_data.get("selftext", "")[:TEXT_CONFIG["MAX_SELFTEXT_LENGTH"]],  # Truncate long text
                                "score": post_data.get("score", 0),
                                "num_comments": post_data.get("num_comments", 0),
                                "subreddit": post_data.get("subreddit", ""),
                                "created_utc": post_data.get("created_utc", 0),
                                "url": post_data.get("url", ""),
                                "permalink": f"https://reddit.com{post_data.get('permalink', '')}"
                            }
                            
                            # Additional filtering for relevance
                            if self._is_relevant_post(post_info, category, query):
                                posts.append(post_info)
                    
                    return (category, posts[:REDDIT_CONFIG["MAX_POSTS_PER_QUERY"]])  # Limit to top 3 per query
                else:
                    logger.warning(f"Reddit API returned status {response.status} for query: {query}")
                    
        except Exception as e:
            logger.error(f"Error in Reddit search for '{query}': {e}")
        
        return None
    
    def _is_relevant_post(self, post: Dict, category: str, query: str) -> bool:
        """Check if a Reddit post is relevant to the category and location"""
        title = post.get("title", "").lower()
        text = post.get("selftext", "").lower()
        combined_text = f"{title} {text}"
        
        # Basic relevance checks
        if len(combined_text) < TEXT_CONFIG["MIN_RELEVANT_TEXT_LENGTH"]:  # Too short
            return False
            
        # Category-specific filtering using constants
        if category in RELEVANCE_KEYWORDS:
            return any(keyword in combined_text for keyword in RELEVANCE_KEYWORDS[category])
        elif category == CategoryType.MISC.value:
            return True  # More lenient for misc category
            
        return True
    
    async def _fetch_google_places_data(self, lat: float, lon: float) -> Dict:
        """Fetch comprehensive data from Google Places API"""
        places_data = {
            "restaurants": [],
            "hangout_spots": [],
            "infrastructure": [],
            "shopping": [],
            "nightlife": [],
            "transit": []
        }
        
        # Use constants for search queries
        search_queries = GOOGLE_PLACES_QUERIES
        
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            async with aiohttp.ClientSession() as session:
                tasks = []
                for query_types, category in search_queries:
                    task = self._search_google_places(session, lat, lon, query_types, category, ssl_context)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, result in enumerate(results):
                    if not isinstance(result, Exception) and result:
                        category = search_queries[i][1]
                        places_data[category] = result
                        
        except Exception as e:
            logger.error(f"Error fetching Google Places data: {e}")
        
        return places_data
    
    async def _search_google_places(self, session, lat: float, lon: float, 
                                  place_types: str, category: str, ssl_context) -> List[Dict]:
        """Search Google Places for specific types"""
        try:
            # Google Places Nearby Search API
            url = GOOGLE_PLACES_CONFIG["BASE_URL"]
            
            params = {
                "location": f"{lat},{lon}",
                "radius": GOOGLE_PLACES_CONFIG["RADIUS"],
                "type": place_types.split("|")[0],  # Use first type
                "key": self.config.GOOGLE_PLACES_API_KEY
            }
            
            async with session.get(url, params=params, ssl=ssl_context) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    places = []
                    for place in data.get("results", [])[:GOOGLE_PLACES_CONFIG["MAX_RESULTS"]]:  # Limit to top 10
                        place_info = {
                            "name": place.get("name"),
                            "rating": place.get("rating", 0),
                            "user_ratings_total": place.get("user_ratings_total", 0),
                            "price_level": place.get("price_level"),
                            "types": place.get("types", []),
                            "vicinity": place.get("vicinity", "")
                        }
                        places.append(place_info)
                    
                    return places
                else:
                    logger.error(f"Google Places API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error in Google Places search: {e}")
        
        return []
    
    def _build_comprehensive_prompt(self, location_slug: str, places_data: Dict, 
                                  reddit_data: Dict, lat: float, lon: float) -> str:
        """Build comprehensive prompt with Google Places and Reddit data"""
        
        # Build context from Google Places data
        context_parts = [f"Location Analysis for: {location_slug} (Lat: {lat}, Lon: {lon})"]
        
        # Add restaurant data
        if places_data.get("restaurants"):
            context_parts.append("\n=== FOOD & RESTAURANTS (Google Places) ===")
            for place in places_data["restaurants"][:TEXT_CONFIG["MAX_RESTAURANTS_DISPLAY"]]:
                rating_info = f"({place['rating']}⭐, {place['user_ratings_total']} reviews)" if place['rating'] else ""
                context_parts.append(f"• {place['name']} {rating_info} - {place['vicinity']}")
        
        # Add Reddit food insights
        if reddit_data.get("food"):
            context_parts.append("\n=== FOOD INSIGHTS FROM REDDIT ===")
            for post in reddit_data["food"][:REDDIT_CONFIG["MAX_POSTS_PER_CATEGORY"]]:
                context_parts.append(f"• Reddit Post: {post['title']} (↑{post['score']}, {post['num_comments']} comments)")
                if post['selftext']:
                    context_parts.append(f"  Content: {post['selftext'][:TEXT_CONFIG['MAX_CONTEXT_LENGTH']]}...")
        
        # Add hangout spots (social spaces)
        if places_data.get("hangout_spots"):
            context_parts.append("\n=== HANGOUT SPOTS & SOCIAL SPACES (Google Places) ===")
            for place in places_data["hangout_spots"][:TEXT_CONFIG["MAX_HANGOUT_SPOTS_DISPLAY"]]:
                context_parts.append(f"• {place['name']} - {place['vicinity']}")
        
        # Add Reddit social insights
        if reddit_data.get("social"):
            context_parts.append("\n=== SOCIAL INSIGHTS FROM REDDIT ===")
            for post in reddit_data["social"][:REDDIT_CONFIG["MAX_POSTS_PER_CATEGORY"]]:
                context_parts.append(f"• Reddit Post: {post['title']} (↑{post['score']}, {post['num_comments']} comments)")
                if post['selftext']:
                    context_parts.append(f"  Content: {post['selftext'][:TEXT_CONFIG['MAX_CONTEXT_LENGTH']]}...")
        
        # Add rental insights from Reddit
        if reddit_data.get("rentals"):
            context_parts.append("\n=== RENTAL INSIGHTS FROM REDDIT ===")
            for post in reddit_data["rentals"][:REDDIT_CONFIG["MAX_POSTS_PER_CATEGORY"]]:
                context_parts.append(f"• Reddit Post: {post['title']} (↑{post['score']}, {post['num_comments']} comments)")
                if post['selftext']:
                    context_parts.append(f"  Content: {post['selftext'][:TEXT_CONFIG['MAX_CONTEXT_LENGTH']]}...")
        
        # Add infrastructure (schools, hospitals, temples)
        if places_data.get("infrastructure"):
            context_parts.append("\n=== INFRASTRUCTURE & INSTITUTIONS ===")
            for place in places_data["infrastructure"][:TEXT_CONFIG["MAX_INFRASTRUCTURE_DISPLAY"]]:
                context_parts.append(f"• {place['name']} - {place['vicinity']}")
        
        # Add shopping
        if places_data.get("shopping"):
            context_parts.append("\n=== SHOPPING & SERVICES ===")
            for place in places_data["shopping"][:TEXT_CONFIG["MAX_SHOPPING_DISPLAY"]]:
                context_parts.append(f"• {place['name']} - {place['vicinity']}")
        
        # Add nightlife (bars/clubs only)
        if places_data.get("nightlife"):
            context_parts.append("\n=== NIGHTLIFE (BARS & CLUBS) ===")
            for place in places_data["nightlife"][:TEXT_CONFIG["MAX_NIGHTLIFE_DISPLAY"]]:
                context_parts.append(f"• {place['name']} - {place['vicinity']}")
        
        # Add Reddit nightlife insights
        if reddit_data.get("nightlife"):
            context_parts.append("\n=== NIGHTLIFE INSIGHTS FROM REDDIT ===")
            for post in reddit_data["nightlife"][:TEXT_CONFIG["MAX_MISC_REDDIT_DISPLAY"]]:
                context_parts.append(f"• Reddit Post: {post['title']} (↑{post['score']}, {post['num_comments']} comments)")
                if post['selftext']:
                    context_parts.append(f"  Content: {post['selftext'][:TEXT_CONFIG['MAX_CONTEXT_LENGTH']]}...")
        
        # Add Reddit misc insights
        if reddit_data.get("misc"):
            context_parts.append("\n=== GENERAL INSIGHTS FROM REDDIT ===")
            for post in reddit_data["misc"][:TEXT_CONFIG["MAX_MISC_REDDIT_DISPLAY"]]:
                context_parts.append(f"• Reddit Post: {post['title']} (↑{post['score']}, {post['num_comments']} comments)")
                if post['selftext']:
                    context_parts.append(f"  Content: {post['selftext'][:TEXT_CONFIG['MAX_CONTEXT_LENGTH']]}...")
        
        context = "\n".join(context_parts)
        
        return f"""
SYSTEM_PROMPTS["LOCATION_EXPERT"].format(location_slug=location_slug)

{context}

Generate a comprehensive JSON response with this structure:
{{
  "summary": "A 2-3 sentence overview highlighting the key characteristics of this area based on available businesses, amenities, and community insights",
  "insights": {{
    "food": [
      {{
        "title": "Restaurant/Food Place Name or insight from Reddit",
        "summary": "Brief description highlighting what makes it notable (cuisine, popularity, etc.) or community opinion",
        "status_tag": StatusTag.POPULAR.value,
        "source_type": SourceType.AI.value
      }}
    ],
    "social": [
      {{
        "title": "Park/Library/Community Space/Hangout Spot Name or Reddit insight", 
        "summary": "Description of the hangout spot and why it's good for socializing (NOT schools or colleges)",
        "source_type": SourceType.AI.value
      }}
    ],
    "rentals": [
      {{
        "title": "Housing/Area insight based on location characteristics or Reddit discussions",
        "summary": "General rental market insights based on area amenities, connectivity, and community discussions",
        "source_type": SourceType.AI.value
      }}
    ],
    "nightlife": [
      {{
        "title": "Bar/Club/Pub Name or Reddit nightlife insight",
        "summary": "Brief description of the bar/club and its atmosphere or community recommendations (ONLY bars, clubs, pubs)",
        "source_type": SourceType.AI.value
      }}
    ],
    "misc": [
      {{
        "title": "Infrastructure/Transportation/Shopping/School/Hospital insight",
        "summary": "Notable infrastructure, connectivity, civic amenities, educational institutions, healthcare, or community concerns",
        "source_type": SourceType.AI.value
      }}
    ]
  }}
}}

IMPORTANT CATEGORY DEFINITIONS:
1. SOCIAL: Only hangout spots like parks, libraries, community centers, recreational areas - NO schools or colleges
2. NIGHTLIFE: Only bars, clubs, pubs - NO general entertainment venues, cinemas, or casual spots
3. MISC: Schools, colleges, hospitals, temples, infrastructure, transportation, markets

IMPORTANT RULES:
1. Combine insights from both Google Places and Reddit data
2. For Reddit insights, prioritize posts with higher scores and more comments
3. For rentals, use Reddit discussions to provide realistic insights about housing costs and availability
4. Focus on the most notable and highly-rated establishments or widely discussed topics
5. Keep descriptions concise but informative
6. Include empty arrays if no relevant data exists for a category
7. When using Reddit insights, make them sound natural (don't mention \"Reddit says\" or \"according to Reddit\")
8. Return ONLY valid JSON, no other text or formatting
"""
    async def _call_openai(self, prompt: str) -> Optional[str]:
        """Call OpenAI API with proper async handling"""
        try:
            # Use the newer OpenAI client for better async support
            client = openai.AsyncClient(api_key=self.config.OPENAI_API_KEY)
            
            # MUST instruct model to return JSON when using response_format json_object
            response = await client.chat.completions.create(
                model=OPENAI_CONFIG["MODEL"],
                messages=[
                    {
                        "role": "system", 
                        "content": SYSTEM_PROMPTS["MAIN"]
                    },
                    {"role": "user", "content": prompt + "\n\nReturn output strictly in JSON format."}
                ],
                max_tokens=OPENAI_CONFIG["MAX_TOKENS"],
                temperature=OPENAI_CONFIG["TEMPERATURE"],
                response_format=OPENAI_CONFIG["RESPONSE_FORMAT"]
            )
            
            raw_response = response.choices[0].message.content.strip()
            
            # DEBUG LOGGING
            print(DEBUG_LABELS["OPENAI_RAW_RESPONSE"])
            print(raw_response)
            print(DEBUG_LABELS["END_RESPONSE"])
            
            return raw_response
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return None
    
    def _parse_ai_response(self, response: str) -> Optional[Dict]:
        """Parse and validate AI response JSON"""
        try:
            # Clean any potential markdown formatting
            if response.startswith("```"):
                response = response.replace("```json", "").replace("```","")
            
            # Remove any potential unicode issues before parsing
            response = response.encode('utf-8', errors='ignore').decode('utf-8')
            
            parsed = json.loads(response)
            
            # Validate required structure
            if "summary" not in parsed or "insights" not in parsed:
                logger.error(ERROR_MESSAGES["MISSING_SUMMARY_OR_INSIGHTS"])
                print(DEBUG_LABELS["INVALID_STRUCTURE"])
                print("Parsed response:", parsed)
                return None
            
            # Ensure all categories exist (even if empty)
            insights = parsed["insights"]
            
            for category in REQUIRED_CATEGORIES:
                if category not in insights:
                    insights[category] = []
            
            # Clean any unicode issues in the parsed data
            def clean_dict_values(obj):
                if isinstance(obj, dict):
                    return {k: clean_dict_values(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [clean_dict_values(item) for item in obj]
                elif isinstance(obj, str):
                    # Remove problematic unicode characters
                    return obj.encode('utf-8', errors='ignore').decode('utf-8')
                else:
                    return obj
            
            parsed = clean_dict_values(parsed)
            
            logger.info(f"Successfully parsed AI response with {len(insights)} categories")
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"{ERROR_MESSAGES['JSON_PARSE_ERROR']}: {str(e)}")
            print(DEBUG_LABELS["JSON_PARSE_ERROR"])
            print("Raw response that failed:", response[:1000])
            return None
        except Exception as e:
            logger.error(f"{ERROR_MESSAGES['JSON_PARSE_ERROR']}: {str(e)}")
            return None
