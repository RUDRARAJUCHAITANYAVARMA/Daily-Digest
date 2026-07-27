import datetime
import logging
import os

import dotenv

dotenv.load_dotenv()

from database import database_creation
from database import store_database
from emails import email_pipeline
from helpers import news_processor
from models import news_fetcher
from news import news_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def pipeline():
    """Execute the daily news aggregation, ranking, summarization, and newsletter distribution pipeline."""

    logger.info("Starting the pipeline")

    date = datetime.datetime.now() - datetime.timedelta(days=2)

    try:
        logger.info("=" * 60)
        logger.info("Starting News Processing Pipeline")
        logger.info("=" * 60)

        # Stage 1: Retrieve news
        logger.info(
            "[Stage 1] Fetching top headlines for %s...", date.strftime("%Y-%m-%d")
        )
        news = news_api.get_top_headlines(date.strftime("%Y-%m-%d"))
        logger.info("[Stage 1] Retrieved %d news articles.", len(news))

        # Stage 2: Initialize database
        logger.info("[Stage 2] Initializing the article database...")
        database_creation.initialize_article_db()
        logger.info("[Stage 2] Database initialized successfully.")

        # Stage 3: Clean raw news data
        logger.info("[Stage 3] Cleaning retrieved news articles...")
        news_cleaned = news_processor.clean_news_data(news)
        logger.info("[Stage 3] Cleaned %d news articles.", len(news_cleaned))

        # Stage 4: Store articles
        logger.info("[Stage 4] Storing cleaned articles in the database...")
        store_database.store_news_in_db(news_cleaned)
        logger.info("[Stage 4] Successfully stored %d articles.", len(news_cleaned))

        # Stage 5: Generate news digest
        logger.info("[Stage 5] Generating the top news digest using the LLM...")
        articles_summarized = news_fetcher.get_top_news_digest()
        logger.info(
            "[Stage 5] Generated %d summarized news articles.",
            len(articles_summarized),
        )

        # Stage 6: Sending Email to subscribed users
        logger.info("[Stage 6] Sending Email to subscribed users...")
        email_pipeline.email_service_pipeline(articles_summarized)
        logger.info("[Stage 6] Successfully sent email to subscribed users.")

        # Stage 7: Clean up
        logger.info("[Stage 7] Removing the temporary database...")
        os.remove("news.db")
        logger.info("[Stage 7] Temporary database removed.")

        logger.info("=" * 60)
        logger.info("News Processing Pipeline completed successfully.")
        logger.info("=" * 60)

    except Exception as e:
        logger.exception(f"Pipeline Failed with Exception: {e}")
        raise


pipeline()
