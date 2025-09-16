"""
Constants for InsightWorker AI processing
"""
from enum import Enum
from typing import Dict, List

class CategoryType(Enum):
    """Insight categories"""
    FOOD = "food"
    SOCIAL = "social"
    RENTALS = "rentals"
    NIGHTLIFE = "nightlife"
    MISC = "misc"

class SourceType(Enum):
    """Source types for insights"""
    AI = "ai"
    USER = "user"

class PlaceType(Enum):
    """Google Places API types"""
    RESTAURANT = "restaurant"
    FOOD = "food"
    CAFE = "cafe"
    BAKERY = "bakery"
    PARK = "park"
    LIBRARY = "library"
    COMMUNITY_CENTER = "community_center"
    RECREATIONAL = "recreational"
    HOSPITAL = "hospital"
    CLINIC = "clinic"
    PHARMACY = "pharmacy"
    DOCTOR = "doctor"
    SCHOOL = "school"
    COLLEGE = "college"
    UNIVERSITY = "university"
    TEMPLE = "temple"
    SHOPPING_MALL = "shopping_mall"
    MARKET = "market"
    STORE = "store"
    ATM = "atm"
    BANK = "bank"
    BAR = "bar"
    CLUB = "club"
    PUB = "pub"
    LOUNGE = "lounge"
    BUS_STATION = "bus_station"
    METRO_STATION = "metro_station"
    TAXI_STAND = "taxi_stand"

class StatusTag(Enum):
    """Status tags for insights"""
    POPULAR = "Popular"
    TRENDING = "Trending"
    RECOMMENDED = "Recommended"
    NEW = "New"
    CLOSED = "Closed"

# Category definitions
CATEGORY_DEFINITIONS: Dict[str, str] = {
    CategoryType.FOOD.value: "Food establishments, restaurants, street food, cafes, bakeries",
    CategoryType.SOCIAL.value: "Hangout spots, community spaces, parks, libraries, recreational areas (NOT schools or colleges)",
    CategoryType.RENTALS.value: "Housing, rental prices, accommodation options, PG, flats",
    CategoryType.NIGHTLIFE.value: "Bars, clubs, pubs exclusively (NOT general entertainment)",
    CategoryType.MISC.value: "Infrastructure, civic issues, transportation, markets, shopping, schools, colleges, hospitals, temples"
}

# Reddit search queries by category
REDDIT_QUERIES: Dict[str, List[str]] = {
    CategoryType.FOOD.value: ["restaurant", "food", "cafe", "street food", "where to eat"],
    CategoryType.SOCIAL.value: ["hangout", "places to visit", "parks", "activities", "weekend"],
    CategoryType.RENTALS.value: ["rent", "rental", "accommodation", "PG", "flat", "housing"],
    CategoryType.NIGHTLIFE.value: ["bars", "clubs", "nightlife", "party", "drinks"],
    CategoryType.MISC.value: ["living in", "infrastructure", "transport", "connectivity", "hospitals", "schools"]
}

# Google Places search queries
GOOGLE_PLACES_QUERIES: List[tuple] = [
    (f"{PlaceType.RESTAURANT.value}|{PlaceType.FOOD.value}|{PlaceType.CAFE.value}|{PlaceType.BAKERY.value}", "restaurants"),
    (f"{PlaceType.PARK.value}|{PlaceType.LIBRARY.value}|{PlaceType.COMMUNITY_CENTER.value}|{PlaceType.RECREATIONAL.value}", "hangout_spots"),
    (f"{PlaceType.HOSPITAL.value}|{PlaceType.CLINIC.value}|{PlaceType.PHARMACY.value}|{PlaceType.DOCTOR.value}|{PlaceType.SCHOOL.value}|{PlaceType.COLLEGE.value}|{PlaceType.UNIVERSITY.value}|{PlaceType.TEMPLE.value}", "infrastructure"),
    (f"{PlaceType.SHOPPING_MALL.value}|{PlaceType.MARKET.value}|{PlaceType.STORE.value}|{PlaceType.ATM.value}|{PlaceType.BANK.value}", "shopping"),
    (f"{PlaceType.BAR.value}|{PlaceType.CLUB.value}|{PlaceType.PUB.value}|{PlaceType.LOUNGE.value}", "nightlife"),
    (f"{PlaceType.BUS_STATION.value}|{PlaceType.METRO_STATION.value}|{PlaceType.TAXI_STAND.value}", "transit")
]

# Reddit API configuration
REDDIT_CONFIG = {
    "BASE_URL": "https://www.reddit.com/search.json",
    "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "SORT": "relevance",
    "TIME_FILTER": "year",
    "LIMIT": 10,
    "MIN_SCORE": 5,
    "MIN_COMMENTS": 2,
    "MAX_POSTS_PER_QUERY": 3,
    "MAX_POSTS_PER_CATEGORY": 5
}

# Google Places API configuration
GOOGLE_PLACES_CONFIG = {
    "BASE_URL": "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
    "RADIUS": 2000,  # 2km radius
    "MAX_RESULTS": 10,
    "MAX_RESULTS_PER_CATEGORY": 8
}

# OpenAI configuration
OPENAI_CONFIG = {
    "MODEL": "gpt-4o-mini",
    "MAX_TOKENS": 3000,
    "TEMPERATURE": 0.2,
    "RESPONSE_FORMAT": {"type": "json_object"}
}

# Text processing configuration
TEXT_CONFIG = {
    "MAX_SELFTEXT_LENGTH": 500,
    "MAX_CONTEXT_LENGTH": 200,
    "MIN_RELEVANT_TEXT_LENGTH": 20,
    "MAX_RESTAURANTS_DISPLAY": 8,
    "MAX_HANGOUT_SPOTS_DISPLAY": 6,
    "MAX_INFRASTRUCTURE_DISPLAY": 6,
    "MAX_SHOPPING_DISPLAY": 6,
    "MAX_NIGHTLIFE_DISPLAY": 5,
    "MAX_MISC_REDDIT_DISPLAY": 3
}

# Category-specific keywords for relevance filtering
RELEVANCE_KEYWORDS = {
    CategoryType.FOOD.value: ["restaurant", "food", "eat", "cafe", "dining", "cuisine"],
    CategoryType.RENTALS.value: ["rent", "rental", "accommodation", "flat", "apartment", "housing", "pg"],
    CategoryType.NIGHTLIFE.value: ["bar", "club", "nightlife", "party", "drinks", "pub"],
    CategoryType.SOCIAL.value: ["hangout", "visit", "places", "activities", "fun", "weekend"]
}

# API response structure
REQUIRED_CATEGORIES = [category.value for category in CategoryType]

# System prompts
SYSTEM_PROMPTS = {
    "MAIN": "You are a local area expert who analyzes business data and community insights to provide accurate locality insights. Always respond ONLY in valid JSON format, nothing else.",
    "LOCATION_EXPERT": "You are a local area expert analyzing real business data from Google Places and community insights from Reddit for {location_slug}. Based on the comprehensive data below, generate insights about this locality."
}

# JSON response template
JSON_RESPONSE_TEMPLATE = {
    "summary": "A 2-3 sentence overview highlighting the key characteristics of this area based on available businesses, amenities, and community insights",
    "insights": {
        category.value: [] for category in CategoryType
    }
}

# Error messages
ERROR_MESSAGES = {
    "MISSING_SUMMARY_OR_INSIGHTS": "Invalid AI response structure - missing summary or insights",
    "JSON_PARSE_ERROR": "JSON parsing error",
    "OPENAI_API_ERROR": "OpenAI API error",
    "REDDIT_API_ERROR": "Reddit API error",
    "GOOGLE_PLACES_ERROR": "Google Places API error",
    "AI_PROCESSING_ERROR": "AI processing error"
}

# Debug output labels
DEBUG_LABELS = {
    "OPENAI_RAW_RESPONSE": "=== OpenAI Raw Response ===",
    "END_RESPONSE": "=== End Response ===",
    "INVALID_STRUCTURE": "=== INVALID STRUCTURE ===",
    "JSON_PARSE_ERROR": "=== JSON PARSE ERROR ===",
    "SENDING_RAW_AI_RESPONSE": "=== Sending RAW AI Response to Backend ===",
    "END_DATA": "=== End Data ===",
    "BACKEND_RESPONSE": "=== Backend Response ===",
    "END_RESPONSE": "=== End Response ==="
}
