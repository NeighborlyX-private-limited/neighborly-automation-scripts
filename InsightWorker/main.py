import sys
import asyncio
import requests
import json
import logging
import re
from ai_processor import AIProcessor
from config import Config
from constants import DEBUG_LABELS


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
        
        # Clean the summary if it exists
        if 'summary' in insights_result:
            clean_summary = clean_text(insights_result['summary'])
            if clean_summary:
                insights_result['summary'] = clean_summary
        
        # Clean text in insights if they exist
        if 'insights' in insights_result:
            for category_slug, category_insights in insights_result['insights'].items():
                for insight in category_insights:
                    if 'title' in insight:
                        clean_title = clean_text(insight['title'])
                        if clean_title:
                            insight['title'] = clean_title
                    
                    if 'summary' in insight:
                        clean_summary_text = clean_text(insight['summary'])
                        if clean_summary_text:
                            insight['summary'] = clean_summary_text
                    
                    if 'status_tag' in insight and insight['status_tag']:
                        clean_status_tag = clean_text(insight['status_tag'])
                        if clean_status_tag:
                            insight['status_tag'] = clean_status_tag
        
        # Send RAW OpenAI response without adding IDs or category UUIDs
        callback_payload = {
            "location_slug": str(location_slug),
            "lat": float(lat),
            "lon": float(lon),
            "raw_ai_response": insights_result  # Raw OpenAI JSON response
        }
        
        # Debug output
        print(DEBUG_LABELS["SENDING_RAW_AI_RESPONSE"])
        print(json.dumps(callback_payload, indent=2, ensure_ascii=True))
        print(DEBUG_LABELS["END_DATA"])
        
        # Send request to backend callback
        try:
            response = requests.post(
                f"{callback_url}/insights/callback",
                json=callback_payload,  # Let requests handle JSON serialization
                headers={
                    'User-Agent': 'InsightWorker/1.0',
                    'Content-Type': 'application/json'
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
        print(DEBUG_LABELS["BACKEND_RESPONSE"])
        print("Status:", response.status_code)
        print("Headers:", dict(response.headers))
        print("Response:", response.text)
        print(DEBUG_LABELS["END_RESPONSE"])
        
        if response.status_code == 200:
            logger.info(f"Successfully sent raw AI response for {location_slug}")
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
    
    # Fix: Use correct indices for command line arguments
    location_slug = sys.argv[1]  # Changed from sys.argv[21] to sys.argv[1]
    lat = float(sys.argv[2])     # Changed from sys.argv[22] to sys.argv[2]
    lon = float(sys.argv[3])     # Changed from sys.argv[23] to sys.argv[3]
    callback_url = sys.argv[4]   # Changed from sys.argv[24] to sys.argv[4]
    
    success = asyncio.run(generate_insights_for_location(location_slug, lat, lon, callback_url))
    sys.exit(0 if success else 1)