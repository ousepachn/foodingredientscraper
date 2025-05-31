from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime, timedelta
import uuid

from app.models.api import (
    ScrapeRequest,
    ScrapeResponse,
    ProductResponse,
    JobStatusResponse,
)
from app.models.product import ProductData, ScrapeJob
from app.services.firebase import FirebaseService
from app.scrapers.traderjoes import TraderJoesScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Product Scraper API",
    description="API for scraping product data from e-commerce sites",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
firebase_service = FirebaseService()
scraper = TraderJoesScraper()


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_product(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """Start a new scraping job"""
    try:
        # Validate URL
        if not scraper.can_handle(request.url):
            raise HTTPException(
                status_code=400, detail="URL not supported by any available scraper"
            )

        # Check if product already exists and force refresh not requested
        if not request.force_refresh:
            existing_product = await firebase_service.get_product_by_url(request.url)
            if existing_product:
                return ScrapeResponse(
                    job_id=None,
                    status="completed",
                    message="Product already exists",
                    product_id=existing_product.id,
                    estimated_completion=datetime.now(),
                )

        # Create new job
        job = ScrapeJob(
            job_id=str(uuid.uuid4()),
            url=request.url,
            status="pending",
            created_at=datetime.now(),
            max_retries=3,
        )

        # Store job in Firebase
        await firebase_service.store_job(job)

        # Start background task
        background_tasks.add_task(
            process_scrape_job,
            job.job_id,
            request.url,
            request.store_in_firebase,
            request.include_nutrition,
            request.webhook_url,
        )

        return ScrapeResponse(
            job_id=job.job_id,
            status="pending",
            message="Scraping job started",
            product_id=None,
            estimated_completion=datetime.now() + timedelta(minutes=5),
        )

    except Exception as e:
        logger.error(f"Error starting scrape job: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error starting scrape job: {str(e)}"
        )


@app.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get status of a scraping job"""
    try:
        job = await firebase_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            progress=100 if job.status in ["completed", "failed"] else 0,
            created_at=job.created_at,
            estimated_completion=job.completed_at
            or (job.created_at + timedelta(minutes=5)),
            result=job.result_product_id if job.status == "completed" else None,
            error=job.error_message if job.status == "failed" else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting job status: {str(e)}"
        )


@app.get("/product/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str):
    """Get product data by ID"""
    try:
        product = await firebase_service.get_product_by_id(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        return ProductResponse(
            product=product, cached=True, last_updated=product.scraped_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting product: {str(e)}")


async def process_scrape_job(
    job_id: str,
    url: str,
    store_in_firebase: bool,
    include_nutrition: bool,
    webhook_url: str | None,
):
    """Process a scraping job in the background"""
    try:
        # Update job status to processing
        job = await firebase_service.get_job(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.mark_processing()
        await firebase_service.update_job_status(job)

        # Scrape product data
        product = await scraper.scrape(url)

        # Store in Firebase if requested
        if store_in_firebase:
            await firebase_service.store_product(product)

        # Update job status
        job.mark_completed(product.id)
        await firebase_service.update_job_status(job)

        # Send webhook notification if URL provided
        if webhook_url:
            # TODO: Implement webhook notification
            pass

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}")

        # Update job status to failed
        job = await firebase_service.get_job(job_id)
        if job:
            job.mark_failed(str(e))
            await firebase_service.update_job_status(job)

        # Send webhook notification if URL provided
        if webhook_url:
            # TODO: Implement webhook notification
            pass
