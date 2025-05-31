import logging
from typing import Optional, List, Dict, Any
import firebase_admin
from firebase_admin import credentials, firestore, storage
from datetime import datetime, timedelta
import hashlib
import json

from app.models.product import ProductData, ScrapeJob


class FirebaseService:
    """Service for interacting with Firebase Firestore and Storage"""

    def __init__(
        self, credentials_path: Optional[str] = None, project_id: Optional[str] = None
    ):
        """Initialize Firebase service with optional credentials"""
        self.credentials_path = credentials_path
        self.project_id = project_id
        self.db = None
        self.bucket = None
        self.logger = logging.getLogger(__name__)

    async def initialize(self) -> bool:
        """Initialize Firebase connection"""
        try:
            if not firebase_admin._apps:
                if self.credentials_path:
                    cred = credentials.Certificate(self.credentials_path)
                else:
                    cred = credentials.ApplicationDefault()

                firebase_admin.initialize_app(
                    cred,
                    {
                        "projectId": self.project_id,
                        "storageBucket": f"{self.project_id}.appspot.com",
                    },
                )

            self.db = firestore.client()
            self.bucket = storage.bucket()
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Firebase: {str(e)}")
            return False

    async def store_product(self, product: ProductData) -> bool:
        """Store product data in Firestore"""
        try:
            if not self.db:
                await self.initialize()

            # Store in products collection
            doc_ref = self.db.collection("products").document(product.id)
            doc_ref.set(product.to_dict())

            # Store URL hash for lookup
            url_hash = self._generate_url_hash(product.url)
            self.db.collection("url_lookup").document(url_hash).set(
                {
                    "product_id": product.id,
                    "url": product.url,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )

            return True
        except Exception as e:
            self.logger.error(f"Failed to store product: {str(e)}")
            return False

    async def get_product_by_url(self, url: str) -> Optional[ProductData]:
        """Retrieve product by URL using hash lookup"""
        try:
            if not self.db:
                await self.initialize()

            url_hash = self._generate_url_hash(url)
            doc = self.db.collection("url_lookup").document(url_hash).get()

            if doc.exists:
                product_id = doc.to_dict()["product_id"]
                return await self.get_product_by_id(product_id)
            return None
        except Exception as e:
            self.logger.error(f"Failed to get product by URL: {str(e)}")
            return None

    async def get_product_by_id(self, product_id: str) -> Optional[ProductData]:
        """Retrieve product by ID"""
        try:
            if not self.db:
                await self.initialize()

            doc = self.db.collection("products").document(product_id).get()
            if doc.exists:
                return ProductData.from_dict(doc.to_dict())
            return None
        except Exception as e:
            self.logger.error(f"Failed to get product by ID: {str(e)}")
            return None

    async def store_job(self, job: ScrapeJob) -> bool:
        """Store scraping job in Firestore"""
        try:
            if not self.db:
                await self.initialize()

            doc_ref = self.db.collection("jobs").document(job.job_id)
            doc_ref.set(
                {
                    "job_id": job.job_id,
                    "url": job.url,
                    "status": job.status,
                    "created_at": job.created_at,
                    "started_at": job.started_at,
                    "completed_at": job.completed_at,
                    "result_product_id": job.result_product_id,
                    "error_message": job.error_message,
                    "retry_count": job.retry_count,
                    "max_retries": job.max_retries,
                    "options": job.options,
                }
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to store job: {str(e)}")
            return False

    async def update_job_status(self, job_id: str, status: str, **kwargs) -> bool:
        """Update job status and optional fields"""
        try:
            if not self.db:
                await self.initialize()

            doc_ref = self.db.collection("jobs").document(job_id)
            update_data = {"status": status}
            update_data.update(kwargs)

            doc_ref.update(update_data)
            return True
        except Exception as e:
            self.logger.error(f"Failed to update job status: {str(e)}")
            return False

    async def get_job(self, job_id: str) -> Optional[ScrapeJob]:
        """Retrieve job by ID"""
        try:
            if not self.db:
                await self.initialize()

            doc = self.db.collection("jobs").document(job_id).get()
            if doc.exists:
                data = doc.to_dict()
                return ScrapeJob(
                    job_id=data["job_id"],
                    url=data["url"],
                    status=data["status"],
                    created_at=data["created_at"],
                    started_at=data.get("started_at"),
                    completed_at=data.get("completed_at"),
                    result_product_id=data.get("result_product_id"),
                    error_message=data.get("error_message"),
                    retry_count=data.get("retry_count", 0),
                    max_retries=data.get("max_retries", 3),
                    options=data.get("options", {}),
                )
            return None
        except Exception as e:
            self.logger.error(f"Failed to get job: {str(e)}")
            return None

    async def store_scrape_log(self, log_data: Dict[str, Any]) -> bool:
        """Store scraping operation log"""
        try:
            if not self.db:
                await self.initialize()

            self.db.collection("scrape_logs").add(
                {**log_data, "timestamp": datetime.utcnow().isoformat()}
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to store scrape log: {str(e)}")
            return False

    async def cleanup_old_jobs(self, days_old: int = 7) -> int:
        """Clean up old completed/failed jobs"""
        try:
            if not self.db:
                await self.initialize()

            cutoff = datetime.utcnow() - timedelta(days=days_old)
            cutoff_str = cutoff.isoformat()

            # Query for old completed/failed jobs
            jobs = (
                self.db.collection("jobs")
                .where("status", "in", ["completed", "failed"])
                .where("completed_at", "<", cutoff_str)
                .stream()
            )

            deleted = 0
            for job in jobs:
                job.reference.delete()
                deleted += 1

            return deleted
        except Exception as e:
            self.logger.error(f"Failed to cleanup old jobs: {str(e)}")
            return 0

    def _generate_url_hash(self, url: str) -> str:
        """Generate consistent hash for URL lookup"""
        return hashlib.sha256(url.encode()).hexdigest()
