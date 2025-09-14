# insights_worker/ai_processor.py
import openai
import json
import logging
import asyncio
import aiohttp
from typing import List, Dict, Optional
from config import Config
import re
from datetime import datetime, timedelta
import urllib.parse


logger = logging.getLogger(__name__)


class AIProcessor:
    def __init__(self):
        self.config = Config()
        openai.api_key = self.config.OPENAI_API_KEY
        
        # Updated categories mapping with clarified definitions
        self.categories = {
            "food": "Food establishments, restaurants, street food, cafes, bakeries",
            "social": "Hangout spots, community spaces, parks, libraries, recreational areas (NOT schools or colleges)",
            "rentals": "Housing, rental prices, accommodation options, PG, flats",
            "nightlife": "Bars, clubs, pubs exclusively (NOT general entertainment)",
            "misc": "Infrastructure, civic issues, transportation, markets, shopping, schools, colleges, hospitals, temples"
        }
        
        # Reddit search configurations
        self.reddit_queries = {
            "food": ["restaurant", "food", "cafe", "street food", "where to eat"],
            "social": ["hangout", "places to visit", "parks", "activities", "weekend"],
            "rentals": ["rent", "rental", "accommodation", "PG", "flat", "housing"],
            "nightlife": ["bars", "clubs", "nightlife", "party", "drinks"],
            "misc": ["living in", "infrastructure", "transport", "connectivity", "hospitals", "schools"]
        }
    
    async def generate_insights(self, location_slug: str, lat: float, lon: float) -> Optional[Dict]:
        """Generate insights using OpenAI + Google Places + Reddit data"""
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
        reddit_data = {
            "food": [],
            "social": [],
            "rentals": [],
            "nightlife": [],
            "misc": []
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Set headers to mimic a browser request
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                tasks = []
                for category, queries in self.reddit_queries.items():
                    for query in queries:
                        # Create search query combining location and topic
                        search_query = f"{location_slug} {query}"
                        task = self._search_reddit(session, search_query, category, headers)
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
    
    async def _search_reddit(self, session, query: str, category: str, headers: Dict) -> Optional[tuple]:
        """Search Reddit for specific query and category"""
        try:
            # Use Reddit's JSON API
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.reddit.com/search.json?q={encoded_query}&sort=relevance&t=year&limit=10"
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    posts = []
                    for post in data.get("data", {}).get("children", []):
                        post_data = post.get("data", {})
                        
                        # Filter for relevance and quality
                        if (post_data.get("score", 0) > 5 and 
                            post_data.get("num_comments", 0) > 2):
                            
                            post_info = {
                                "title": post_data.get("title", ""),
                                "selftext": post_data.get("selftext", "")[:500],  # Truncate long text
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
                    
                    return (category, posts[:3])  # Limit to top 3 per query
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
        if len(combined_text) < 20:  # Too short
            return False
            
        # Category-specific filtering
        if category == "food":
            food_keywords = ["restaurant", "food", "eat", "cafe", "dining", "cuisine"]
            return any(keyword in combined_text for keyword in food_keywords)
        elif category == "rentals":
            rental_keywords = ["rent", "rental", "accommodation", "flat", "apartment", "housing", "pg"]
            return any(keyword in combined_text for keyword in rental_keywords)
        elif category == "nightlife":
            night_keywords = ["bar", "club", "nightlife", "party", "drinks", "pub"]
            return any(keyword in combined_text for keyword in night_keywords)
        elif category == "social":
            social_keywords = ["hangout", "visit", "places", "activities", "fun", "weekend"]
            return any(keyword in combined_text for keyword in social_keywords)
        elif category == "misc":
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
        
        # Define search queries for different categories with updated definitions
        search_queries = [
            ("restaurant|food|cafe|bakery", "restaurants"),
            ("park|library|community_center|recreational", "hangout_spots"), 
            ("hospital|clinic|pharmacy|doctor|school|college|university|temple", "infrastructure"),
            ("shopping_mall|market|store|atm|bank", "shopping"),
            ("bar|club|pub|lounge", "nightlife"),
            ("bus_station|metro_station|taxi_stand", "transit")
        ]
        
        try:
            async with aiohttp.ClientSession() as session:
                tasks = []
                for query_types, category in search_queries:
                    task = self._search_google_places(session, lat, lon, query_types, category)
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
                                  place_types: str, category: str) -> List[Dict]:
        """Search Google Places for specific types"""
        try:
            # Google Places Nearby Search API
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            
            params = {
                "location": f"{lat},{lon}",
                "radius": 2000,  # 2km radius
                "type": place_types.split("|")[0],  # Use first type
                "key": self.config.GOOGLE_PLACES_API_KEY
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    places = []
                    for place in data.get("results", [])[:10]:  # Limit to top 10
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
            for place in places_data["restaurants"][:8]:
                rating_info = f"({place['rating']}⭐, {place['user_ratings_total']} reviews)" if place['rating'] else ""
                context_parts.append(f"• {place['name']} {rating_info} - {place['vicinity']}")
        
        # Add Reddit food insights
        if reddit_data.get("food"):
            context_parts.append("\n=== FOOD INSIGHTS FROM REDDIT ===")
            for post in reddit_data["food"][:5]:
                context_parts.append(f"• Reddit Post: {post['title']} (↑{post['score']}, {post['num_comments']} comments)")
                if post['selftext']:
                    context_parts.append(f"  Content: {post['selftext'][:200]}...")
        
        # Add hangout spots (social spaces)
        if places_data.get("hangout_spots"):
            context_parts.append("\n=== HANGOUT SPOTS & SOCIAL SPACES (Google Places) ===")
            for place in places_data["hangout_spots"][:6]:
                context_parts.append(f"• {place['name']} - {place['vicinity']}")
        
        # Add Reddit social insights
        if reddit_data.get("social"):
            context_parts.append("\n=== SOCIAL INSIGHTS FROM REDDIT ===")
            for post in reddit_data["social"][:5]:
                context_parts.append(f"• Reddit Post: {post['title']} (↑{post['score']}, {post['num_comments']} comments)")
                if post['selftext']:
                    context_parts.append(f"  Content: {post['selftext'][:200]}...")
        
        # Add rental insights from Reddit
        if reddit_data.get("rentals"):
            context_parts.append("\n=== RENTAL INSIGHTS FROM REDDIT ===")
            for post in reddit_data["rentals"][:5]:
                context_parts.append(f"• Reddit Post: {post['title']} (↑{post['score']}, {post['num_comments']} comments)")
                if post['selftext']:
                    context_parts.append(f"  Content: {post['selftext'][:200]}...")
        
        # Add infrastructure (schools, hospitals, temples)
        if places_data.get("infrastructure"):
            context_parts.append("\n=== INFRASTRUCTURE & INSTITUTIONS ===")
            for place in places_data["infrastructure"][:6]:
                context_parts.append(f"• {place['name']} - {place['vicinity']}")
        
        # Add shopping
        if places_data.get("shopping"):
            context_parts.append("\n=== SHOPPING & SERVICES ===")
            for place in places_data["shopping"][:6]:
                context_parts.append(f"• {place['name']} - {place['vicinity']}")
        
        # Add nightlife (bars/clubs only)
        if places_data.get("nightlife"):
            context_parts.append("\n=== NIGHTLIFE (BARS & CLUBS) ===")
            for place in places_data["nightlife"][:5]:
                context_parts.append(f"• {place['name']} - {place['vicinity']}")
        
        # Add Reddit nightlife insights
        if reddit_data.get("nightlife"):
            context_parts.append("\n=== NIGHTLIFE INSIGHTS FROM REDDIT ===")
            for post in reddit_data["nightlife"][:3]:
                context_parts.append(f"• Reddit Post: {post['title']} (↑{post['score']}, {post['num_comments']} comments)")
                if post['selftext']:
                    context_parts.append(f"  Content: {post['selftext'][:200]}...")
        
        # Add Reddit misc insights
        if reddit_data.get("misc"):
            context_parts.append("\n=== GENERAL INSIGHTS FROM REDDIT ===")
            for post in reddit_data["misc"][:3]:
                context_parts.append(f"• Reddit Post: {post['title']} (↑{post['score']}, {post['num_comments']} comments)")
                if post['selftext']:
                    context_parts.append(f"  Content: {post['selftext'][:200]}...")
        
        context = "\n".join(context_parts)
        
        return f"""
You are a local area expert analyzing real business data from Google Places and community insights from Reddit for {location_slug}. 
Based on the comprehensive data below, generate insights about this locality.

{context}

Generate a comprehensive JSON response with this structure:
{{
  "summary": "A 2-3 sentence overview highlighting the key characteristics of this area based on available businesses, amenities, and community insights",
  "insights": {{
    "food": [
      {{
        "title": "Restaurant/Food Place Name or insight from Reddit",
        "summary": "Brief description highlighting what makes it notable (cuisine, popularity, etc.) or community opinion",
        "status_tag": "Popular" (for highly rated places with 100+ reviews or highly upvoted Reddit posts),
        "source_type": "ai"
      }}
    ],
    "social": [
      {{
        "title": "Park/Library/Community Space/Hangout Spot Name or Reddit insight", 
        "summary": "Description of the hangout spot and why it's good for socializing (NOT schools or colleges)",
        "source_type": "ai"
      }}
    ],
    "rentals": [
      {{
        "title": "Housing/Area insight based on location characteristics or Reddit discussions",
        "summary": "General rental market insights based on area amenities, connectivity, and community discussions",
        "source_type": "ai"
      }}
    ],
    "nightlife": [
      {{
        "title": "Bar/Club/Pub Name or Reddit nightlife insight",
        "summary": "Brief description of the bar/club and its atmosphere or community recommendations (ONLY bars, clubs, pubs)",
        "source_type": "ai"
      }}
    ],
    "misc": [
      {{
        "title": "Infrastructure/Transportation/Shopping/School/Hospital insight",
        "summary": "Notable infrastructure, connectivity, civic amenities, educational institutions, healthcare, or community concerns",
        "source_type": "ai"
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
7. When using Reddit insights, make them sound natural (don't mention "Reddit says" or "according to Reddit")
8. Return ONLY valid JSON, no other text or formatting
"""

    async def _call_openai(self, prompt: str) -> Optional[str]:
        """Call OpenAI API with proper async handling"""
        try:
            # Use the newer OpenAI client for better async support
            client = openai.AsyncClient(api_key=self.config.OPENAI_API_KEY)
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a local area expert who analyzes business data and community insights to provide accurate locality insights. You combine official business data with real community discussions to give comprehensive area analysis."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3000,  # Increased for more comprehensive responses
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            raw_response = response.choices[0].message.content.strip()
            
            # DEBUG LOGGING
            print("=== OpenAI Raw Response ===")
            print(raw_response)
            print("=== End Response ===")
            
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
                logger.error("Invalid AI response structure - missing summary or insights")
                print("=== INVALID STRUCTURE ===")
                print("Parsed response:", parsed)
                return None
            
            # Ensure all categories exist (even if empty)
            required_categories = ["food", "social", "rentals", "nightlife", "misc"]
            insights = parsed["insights"]
            
            for category in required_categories:
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
            logger.error(f"JSON parsing error: {str(e)}")
            print("=== JSON PARSE ERROR ===")
            print("Raw response that failed:", response[:1000])
            return None
        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            return None