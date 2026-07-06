import os
import logging
from datetime import timedelta
from datetime import datetime
from news.news_api import get_top_headlines
from helpers.news_processor import clean_news_data
from database.store_database import store_news_in_db
from models.news_fetcher import get_top_news_digest
from emails.email_pipeline import email_service_pipeline
from database.database_creation import initialize_article_db

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def pipeline():

    logger.info("Starting the pipeline")

    date = datetime.now() - timedelta(days=2)

    try:

        logger.info("=" * 60)
        logger.info("Starting News Processing Pipeline")
        logger.info("=" * 60)

        # Stage 1: Retrieve news
        logger.info(
            "[Stage 1] Fetching top headlines for %s...", date.strftime("%Y-%m-%d")
        )
        news = get_top_headlines(date.strftime("%Y-%m-%d"))
        logger.info("[Stage 1] Retrieved %d news articles.", len(news))

        # Stage 2: Initialize database
        logger.info("[Stage 2] Initializing the article database...")
        initialize_article_db()
        logger.info("[Stage 2] Database initialized successfully.")

        # Stage 3: Clean raw news data
        logger.info("[Stage 3] Cleaning retrieved news articles...")
        cleaned_news = clean_news_data(news)
        logger.info("[Stage 3] Cleaned %d news articles.", len(cleaned_news))

        # Stage 4: Store articles
        logger.info("[Stage 4] Storing cleaned articles in the database...")
        store_news_in_db(cleaned_news)
        logger.info("[Stage 4] Successfully stored %d articles.", len(cleaned_news))

        # Stage 5: Generate news digest
        logger.info("[Stage 5] Generating the top news digest using the LLM...")
        summarized_articles = get_top_news_digest()
        logger.info(
            "[Stage 5] Generated %d summarized news articles.",
            len(summarized_articles),
        )

        # Stage 6: Sending Email to subscribed users
        logger.info("[Stage 6] Sending Email to subscribed users...")
        email_service_pipeline(summarized_articles)
        logger.info("[Stage 6] Successfully sent email to subscribed users.")

        # Stage 7: Clean up
        logger.info("[Stage 7] Removing the temporary database...")
        os.remove("news.db")
        logger.info("[Stage 7] Temporary database removed.")

        logger.info("=" * 60)
        logger.info("News Processing Pipeline completed successfully.")
        logger.info("=" * 60)

    except Exception as e:
        logger.exception("Pipeline Failed with Exception")
        raise


pipeline()
