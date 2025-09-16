import os
from dotenv import load_dotenv

# Load environment variables from config.env file
load_dotenv('config.env')

class Config:
    def __init__(self):
        # OpenAI Configuration
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        
        # Google Places API Configuration
        self.GOOGLE_PLACES_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY')
        
        # PostgreSQL Database Configuration
        self.PG_HOST = os.getenv('PG_HOST', 'localhost')
        self.PG_PORT = int(os.getenv('PG_PORT', 5432))
        self.PG_USER = os.getenv('PG_USER')
        self.PG_PASSWORD = os.getenv('PG_PASSWORD')
        self.PG_DATABASE = os.getenv('PG_DATABASE')
    
    def validate(self):
        """Validate that all required configuration is present"""
        required_vars = [
            'OPENAI_API_KEY',
            'GOOGLE_PLACES_API_KEY',
            'PG_USER',
            'PG_PASSWORD',
            'PG_DATABASE'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(self, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
