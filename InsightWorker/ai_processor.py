# insights_worker/ai_processor.py
import openai
import json
import logging
import asyncio
import aiohttp
from typing import List, Dict, Optional
from config import Config

logger = logging.getLogger(__name__)

class AIProcessor:
    def __init__(self):
        self.config = Config()
        openai.api_key = self.config.OPENAI_API_KEY
        
        # Categories mapping
        self.categories = {
            "food": "Food establishments, restaurants, street food, cafes, bakeries",
            "social": "Community spaces, schools, colleges, libraries, parks, hospitals, temples",
            "rentals": "Housing, rental prices, accommodation options, PG, flats",
            "nightlife": "Bars, clubs, pubs, evening entertainment, lounges",
            "misc": "Infrastructure, civic issues, transportation, markets, shopping"
        }
    
    async def generate_insights(self, location_slug: str, lat: float, lon: float) -> Optional[Dict]:
        """Generate insights using OpenAI + Google Places data"""
        try:
            logger.info(f"Starting AI insight generation for {location_slug}")
            
            # Step 1: Get Google Places data for the area
            places_data = await self._fetch_google_places_data(lat, lon)
            
            # Step 2: Create comprehensive prompt with location data
            prompt = self._build_comprehensive_prompt(location_slug, places_data, lat, lon)
            
            # Step 3: Call OpenAI with rich context
            response = await self._call_openai(prompt)
            
            if response:
                return self._parse_ai_response(response)
            
            return None
            
        except Exception as e:
            logger.error(f"AI processing error: {str(e)}")
            return None
    
    async def _fetch_google_places_data(self, lat: float, lon: float) -> Dict:
        """Fetch comprehensive data from Google Places API"""
        places_data = {
            "restaurants": [],
            "schools": [],
            "hospitals": [],
            "shopping": [],
            "entertainment": [],
            "transit": []
        }
        
        # Define search queries for different categories
        search_queries = [
            ("restaurant|food|cafe|bakery", "restaurants"),
            ("school|college|university|library", "schools"), 
            ("hospital|clinic|pharmacy|doctor", "hospitals"),
            ("shopping_mall|market|store|atm|bank", "shopping"),
            ("bar|club|pub|lounge|cinema|park", "entertainment"),
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
                                  lat: float, lon: float) -> str:
        """Build comprehensive prompt with Google Places data"""
        
        # Build context from Google Places data
        context_parts = [f"Location Analysis for: {location_slug} (Lat: {lat}, Lon: {lon})"]
        
        # Add restaurant data
        if places_data.get("restaurants"):
            context_parts.append("\n=== FOOD & RESTAURANTS ===")
            for place in places_data["restaurants"][:8]:
                rating_info = f"({place['rating']}⭐, {place['user_ratings_total']} reviews)" if place['rating'] else ""
                context_parts.append(f"• {place['name']} {rating_info} - {place['vicinity']}")
        
        # Add schools/social spaces
        if places_data.get("schools"):
            context_parts.append("\n=== EDUCATION & SOCIAL SPACES ===")
            for place in places_data["schools"][:6]:
                context_parts.append(f"• {place['name']} - {place['vicinity']}")
        
        # Add healthcare
        if places_data.get("hospitals"):
            context_parts.append("\n=== HEALTHCARE ===")
            for place in places_data["hospitals"][:5]:
                context_parts.append(f"• {place['name']} - {place['vicinity']}")
        
        # Add shopping
        if places_data.get("shopping"):
            context_parts.append("\n=== SHOPPING & SERVICES ===")
            for place in places_data["shopping"][:6]:
                context_parts.append(f"• {place['name']} - {place['vicinity']}")
        
        # Add entertainment/nightlife
        if places_data.get("entertainment"):
            context_parts.append("\n=== ENTERTAINMENT & NIGHTLIFE ===")
            for place in places_data["entertainment"][:5]:
                context_parts.append(f"• {place['name']} - {place['vicinity']}")
        
        context = "\n".join(context_parts)
        
        return f"""
You are a local area expert analyzing real business and location data for {location_slug}. 
Based on the Google Places data below, generate insights about this locality.

{context}

Generate a comprehensive JSON response with this structure:
{{
  "summary": "A 2-3 sentence overview highlighting the key characteristics of this area based on available businesses and amenities",
  "insights": {{
    "food": [
      {{
        "title": "Restaurant/Food Place Name",
        "summary": "Brief description highlighting what makes it notable (cuisine, popularity, etc.)",
        "status_tag": "Popular" (for highly rated places with 100+ reviews),
        "source_type": "ai"
      }}
    ],
    "social": [
      {{
        "title": "School/College/Hospital/Community Space Name", 
        "summary": "Description of the institution and its significance",
        "source_type": "ai"
      }}
    ],
    "rentals": [
      {{
        "title": "Housing/Area insight based on location characteristics",
        "summary": "General rental market insights based on area amenities and connectivity",
        "source_type": "ai"
      }}
    ],
    "nightlife": [
      {{
        "title": "Bar/Club/Entertainment Venue Name",
        "summary": "Brief description of the venue type and atmosphere",
        "source_type": "ai"
      }}
    ],
    "misc": [
      {{
        "title": "Infrastructure/Transportation/Shopping insight",
        "summary": "Notable infrastructure, connectivity, or civic amenities",
        "source_type": "ai"
      }}
    ]
  }}
}}

IMPORTANT RULES:
1. Only mention businesses/places that appear in the provided data
2. For rentals, do NOT invent specific rental prices
3. For rentals, provide area-based insights
4. Focus on the most notable and highly-rated establishments
5. Keep descriptions concise but informative
6. Include empty arrays if no relevant data exists for a category
7. Return ONLY valid JSON, no other text or formatting
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
                        "content": "You are a local area expert who analyzes business data to provide accurate locality insights. You only mention establishments that exist in the provided data."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2500,
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
                response = response.replace("```json", "").replace("```", "")
            
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
