# insights_worker/main.py

import sys
import asyncio
import requests
import json
import logging
import uuid
import re
from ai_processor import AIProcessor
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_text(text):
    """Clean text by removing emojis, unicode characters, and normalizing"""
    if not text:
        return None
    
    # Remove emojis and other unicode symbols
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002500-\U00002BEF"  # chinese char
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937"
        u"\U00010000-\U0010ffff"
        u"\u2640-\u2642" 
        u"\u2600-\u2B55"
        u"\u200d"
        u"\u23cf"
        u"\u23e9"
        u"\u231a"
        u"\ufe0f"  # dingbats
        u"\u3030"
        "]+", flags=re.UNICODE)
    
    # Remove emojis
    cleaned = emoji_pattern.sub('', text)
    
    # Remove any remaining non-printable characters except basic punctuation
    cleaned = ''.join(c for c in cleaned if c.isprintable() or c in '\n\r\t')
    
    # Clean up extra whitespace and normalize
    cleaned = ' '.join(cleaned.split())
    
    # Ensure we return ASCII-safe string
    return cleaned.encode('ascii', 'ignore').decode('ascii').strip() if cleaned.strip() else None

def get_categories_map(callback_url):
    """Fetch category slug to UUID mapping from backend"""
    try:
        response = requests.get(f"{callback_url}/insights/categories", timeout=10)
        if response.status_code == 200:
            categories = response.json()
            return {cat['slug']: cat['id'] for cat in categories}
    except Exception as e:
        logger.error(f"Failed to fetch categories: {e}")
    return {}

async def generate_insights_for_location(location_slug, lat, lon, callback_url):
    """Main function to generate insights for a location"""
    try:
        logger.info(f"Starting insights generation for {location_slug}")
        
        config = Config()
        config.validate()
        
        ai_processor = AIProcessor()
        insights_result = await ai_processor.generate_insights(location_slug, lat, lon)
        
        if not insights_result:
            logger.error("AI processing failed")
            return False
        
        # Fetch category mapping from backend
        category_map = get_categories_map(callback_url)
        logger.info(f"Retrieved categories: {list(category_map.keys())}")
        
        # Clean the summary
        clean_summary = clean_text(insights_result.get('summary', ''))
        if not clean_summary:
            logger.error("No valid summary generated")
            return False
        
        # Transform insights to array format with UUIDs - exactly as backend expects
        insights_array = []
        if 'insights' in insights_result:
            for category_slug, category_insights in insights_result['insights'].items():
                category_id = category_map.get(category_slug)
                if not category_id:
                    logger.warning(f"Category '{category_slug}' not found in backend")
                    continue
                
                for insight in category_insights:
                    # Generate a UUID for each insight
                    insight_id = str(uuid.uuid4())
                    
                    # Clean all text fields - ensure ASCII only
                    clean_title = clean_text(insight.get('title', ''))
                    clean_summary_text = clean_text(insight.get('summary', ''))
                    clean_status_tag = clean_text(insight.get('status_tag'))
                    
                    if clean_title and clean_summary_text:
                        insights_array.append({
                            "id": insight_id,
                            "category_id": str(category_id),  # Ensure string
                            "title": clean_title,
                            "summary": clean_summary_text,
                            "status_tag": clean_status_tag,
                            "source_type": "ai",
                            "cheers": 0,  # Add default values backend expects
                            "boos": 0
                        })
        
        # Build the exact payload structure the backend callback expects
        callback_payload = {
            "location_slug": str(location_slug),
            "summary": clean_summary,
            "lat": float(lat),
            "lon": float(lon),
            "categories": {},  # Backend expects this field
            "insights": insights_array
        }
        
        # Debug output
        print("=== Sending to Backend ===")
        print(json.dumps(callback_payload, indent=2, ensure_ascii=True))
        print("=== End Data ===")
        
        # Use the exact same approach as requests would for JSON
        # This ensures the Content-Type and encoding are exactly right
        try:
            response = requests.post(
                f"{callback_url}/insights/callback",
                json=callback_payload,  # Let requests handle JSON serialization
                headers={
                    'User-Agent': 'InsightWorker/1.0'
                },
                timeout=60
            )
        except requests.exceptions.JSONDecodeError as e:
            logger.error(f"JSON encoding error: {e}")
            return False
        except Exception as e:
            logger.error(f"Request error: {e}")
            return False
        
        # Debug backend response
        print("=== Backend Response ===")
        print("Status:", response.status_code)
        print("Headers:", dict(response.headers))
        print("Response:", response.text)
        print("=== End Response ===")
        
        if response.status_code == 200:
            logger.info(f"Successfully sent insights for {location_slug}")
            return True
        else:
            logger.error(f"Callback failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error generating insights: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python main.py <location_slug> <lat> <lon> <callback_url>")
        sys.exit(1)
    
    location_slug = sys.argv[1]
    lat = float(sys.argv[2])
    lon = float(sys.argv[3])
    callback_url = sys.argv[4]
    
    success = asyncio.run(generate_insights_for_location(location_slug, lat, lon, callback_url))
    sys.exit(0 if success else 1)
