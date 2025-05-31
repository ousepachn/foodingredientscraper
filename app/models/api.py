from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, Any


class ScrapeRequest(BaseModel):
    """API request model for scraping operations"""

    url: HttpUrl = Field(..., description="Product URL to scrape")
    store_in_firebase: bool = Field(
        True, description="Whether to store results in Firebase"
    )
    include_nutrition: bool = Field(
        False, description="Whether to extract nutrition facts"
    )
    force_refresh: bool = Field(False, description="Force re-scrape even if cached")
    webhook_url: Optional[HttpUrl] = Field(
        None, description="Webhook for completion notification"
    )


class ScrapeResponse(BaseModel):
    """API response model for scraping operations"""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status")
    message: str = Field(..., description="Human-readable status message")
    product_id: Optional[str] = Field(None, description="Product ID if completed")
    estimated_completion: Optional[str] = Field(
        None, description="Estimated completion time"
    )


class ProductResponse(BaseModel):
    """API response model for product data"""

    product: Dict[str, Any] = Field(..., description="Complete product data")
    cached: bool = Field(..., description="Whether result was cached")
    last_updated: str = Field(..., description="Last update timestamp")


class JobStatusResponse(BaseModel):
    """API response model for job status queries"""

    job_id: str
    status: str
    progress: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Completion percentage"
    )
    created_at: str
    estimated_completion: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
