# insights_worker/config.py

class Config:
    # Database
    PG_HOST = "PG_HOST"
    PG_PORT = 5432
    PG_USER = "User" 
    PG_PASSWORD = "Password"
    PG_DATABASE = "DB_NAME"
    
    # APIs
    OPENAI_API_KEY = "openAIkey"  # You need to get this from OpenAI
    GOOGLE_PLACES_API_KEY = "googlekey"
    
    # Logging
    LOG_LEVEL = "INFO"
    
    def validate(self):
        """Validate required environment variables"""
        required = [
            'PG_USER', 'PG_PASSWORD', 'PG_DATABASE',
            'OPENAI_API_KEY', 'GOOGLE_PLACES_API_KEY'
        ]
        
        missing = [key for key in required if not getattr(self, key) or getattr(self, key) == "your_openai_api_key_here"]
        if missing:
            raise ValueError(f"Missing or placeholder values for: {missing}")
