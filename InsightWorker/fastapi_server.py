import json
import logging
import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn

# Ensure the worker directory is in the path
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import generate_insights_for_location

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="InsightWorker API",
    description="AI-powered location insights generation service",
    version="1.0.0"
)

# The URL of the main application's callback endpoint
CALLBACK_URL = "http://localhost:5000"

class InsightRequest(BaseModel):
    location_slug: str
    lat: float
    lon: float
    callback_url: Optional[str] = None

class InsightResponse(BaseModel):
    status: str
    message: str
    location_slug: str

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "InsightWorker API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "InsightWorker",
        "version": "1.0.0"
    }

@app.post("/generate", response_model=InsightResponse)
async def generate_insights(request: InsightRequest, background_tasks: BackgroundTasks):
    """
    Endpoint to trigger AI insight generation.
    This endpoint accepts the request and starts background processing.
    """
    try:
        logger.info(f"Received request to generate insights for {request.location_slug}")
        
        # Use provided callback URL or default
        callback_url = request.callback_url or CALLBACK_URL
        
        # Add the insight generation task to background tasks
        background_tasks.add_task(
            generate_insights_for_location,
            request.location_slug,
            request.lat,
            request.lon,
            callback_url
        )
        
        logger.info(f"Background task started for {request.location_slug}")
        
        return InsightResponse(
            status="accepted",
            message="Insight generation started",
            location_slug=request.location_slug
        )
        
    except Exception as e:
        logger.error(f"Error processing generate request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/generate-sync")
async def generate_insights_sync(request: InsightRequest):
    """
    Synchronous endpoint that waits for insight generation to complete.
    Use this for testing or when you need immediate results.
    """
    try:
        logger.info(f"Received sync request to generate insights for {request.location_slug}")
        
        # Use provided callback URL or default
        callback_url = request.callback_url or CALLBACK_URL
        
        # Run the insight generation synchronously
        success = await generate_insights_for_location(
            request.location_slug,
            request.lat,
            request.lon,
            callback_url
        )
        
        if success:
            return {
                "status": "success",
                "message": "Insights generated successfully",
                "location_slug": request.location_slug
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to generate insights")
            
    except Exception as e:
        logger.error(f"Error in sync insight generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    uvicorn.run(
        "fastapi_server:app",
        host="0.0.0.0",
        port=4269,
        reload=True,
        log_level="info"
    )
