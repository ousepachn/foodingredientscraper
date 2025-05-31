from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


@dataclass
class ProductData:
    """
    Core product data model for scraped products.

    This model represents a complete product scraped from any e-commerce site.
    All scraped data should conform to this structure before Firebase storage.
    """

    # Core identifiers
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = ""

    # Product information
    product_name: str = ""
    brand: Optional[str] = None
    description: Optional[str] = None
    price: Optional[str] = None

    # Ingredients and nutrition
    ingredients: List[str] = field(default_factory=list)
    allergens: Optional[List[str]] = None
    nutrition_facts: Optional[Dict[str, Any]] = None

    # Scraping metadata
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    scrape_duration: float = 0.0
    scrape_status: str = "pending"  # pending, success, failed
    error_message: Optional[str] = None
    scraper_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firebase storage"""
        return {
            "id": self.id,
            "url": self.url,
            "product_name": self.product_name,
            "brand": self.brand,
            "description": self.description,
            "price": self.price,
            "ingredients": self.ingredients,
            "allergens": self.allergens,
            "nutrition_facts": self.nutrition_facts,
            "scraped_at": self.scraped_at,
            "scrape_duration": self.scrape_duration,
            "scrape_status": self.scrape_status,
            "error_message": self.error_message,
            "scraper_version": self.scraper_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductData":
        """Create instance from Firebase document"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            url=data.get("url", ""),
            product_name=data.get("product_name", ""),
            brand=data.get("brand"),
            description=data.get("description"),
            price=data.get("price"),
            ingredients=data.get("ingredients", []),
            allergens=data.get("allergens"),
            nutrition_facts=data.get("nutrition_facts"),
            scraped_at=data.get("scraped_at", datetime.utcnow().isoformat()),
            scrape_duration=data.get("scrape_duration", 0.0),
            scrape_status=data.get("scrape_status", "pending"),
            error_message=data.get("error_message"),
            scraper_version=data.get("scraper_version", "1.0.0"),
        )

    def is_valid(self) -> bool:
        """Validate product data completeness"""
        return bool(
            self.product_name
            and self.url
            and self.ingredients
            and self.scrape_status in ["pending", "success", "failed"]
        )


@dataclass
class ScrapeJob:
    """
    Represents a scraping job for async processing.

    Jobs track the lifecycle of scraping operations and provide
    status updates to API clients.
    """

    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = ""
    status: str = "pending"  # pending, processing, completed, failed
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_product_id: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    # Job configuration
    options: Dict[str, Any] = field(default_factory=dict)

    def mark_processing(self) -> None:
        """Mark job as currently processing"""
        self.status = "processing"
        self.started_at = datetime.utcnow().isoformat()

    def mark_completed(self, product_id: str) -> None:
        """Mark job as successfully completed"""
        self.status = "completed"
        self.completed_at = datetime.utcnow().isoformat()
        self.result_product_id = product_id

    def mark_failed(self, error: str) -> None:
        """Mark job as failed with error message"""
        self.status = "failed"
        self.completed_at = datetime.utcnow().isoformat()
        self.error_message = error
        self.retry_count += 1
