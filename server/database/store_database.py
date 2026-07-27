import logging
import sqlite3

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def store_news_in_db(news_cleaned: list, name_db: str = "news.db"):
    """Store the cleaned news articles in the database.

    Args:
        news_cleaned (list): List of cleaned news articles.
        name_db (str): Name of the database file.
    """

    connection = None
    try:
        connection = sqlite3.connect(name_db)
        cursor = connection.cursor()

        for article in news_cleaned:
            cursor.execute(
                """
                INSERT INTO articles (title, description, content) VALUES (?, ?, ?)
                """,
                (article["title"], article["description"], article["content"]),
            )
        connection.commit()

    except Exception as e:
        logger.exception(f"Failed to store news in database: {e}")
        raise
    finally:
        if connection:
            connection.close()
