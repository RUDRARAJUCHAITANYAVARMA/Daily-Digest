import logging
import sqlite3

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def initialize_article_db(name_db: str = "news.db"):
    """Initialize the SQLite database and create the articles table if it does not exist.

    Args:
        name_db (str): Name of the database file.
    """

    connection = None
    try:
        connection = sqlite3.connect(name_db)
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                content TEXT NOT NULL
            )
            """
        )

        connection.commit()
        logger.info(f"Successfully initialized database '{name_db}'")

    except Exception as e:
        logger.exception(f"Failed to initialize database '{name_db}': {e}")
        raise
    finally:
        if connection:
            connection.close()
