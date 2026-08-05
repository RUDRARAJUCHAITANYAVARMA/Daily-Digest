import json
import logging
import os
import sqlite3

import dotenv
import groq

from helpers import news_processor
from models import prompts

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

client = groq.Groq(api_key=os.getenv("LLM_API_KEY"))




def fetch_article_titles(name_db: str = "news.db") -> list:
    """Retrieve the ID and title of every article stored in the database.

    Args:
        name_db (str): Name of the database file.

    Returns:
        list: List of (article_id, title) tuples.
    """

    connection = None
    try:
        connection = sqlite3.connect(name_db)
        cursor = connection.cursor()

        cursor.execute("SELECT id, title FROM articles")
        articles = cursor.fetchall()

        return [title for title in articles]

    except Exception as e:
        logger.exception(f"Failed to fetch news from database: {e}")
        raise
    finally:
        if connection:
            connection.close()


def rank_top_news_articles(news: list) -> str:
    """Identify the ten most important global news stories using the LLM.

    Args:
        news (list): List of article IDs and titles.

    Returns:
        str: Raw JSON response produced by the LLM.
    """

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompts.TOP_10_NEWS_RETRIEVAL_PROMPT.replace(
                    "{{NEWS_LIST}}", str(news)
                ),
            }
        ],
        temperature=1,
        max_completion_tokens=1024,
        top_p=1,
        stream=True,
        stop=None,
        response_format={"type": "json_object"},
    )

    chunks = [
        chunk.choices[0].delta.content
        for chunk in completion
        if chunk.choices[0].delta.content
    ]
    return "".join(chunks)


def fetch_article_details(news_top: list, name_db: str = "news.db") -> list:
    """Retrieve the complete article information for the selected top news.

    Args:
        news_top (list): Ranked articles returned by the LLM.
        name_db (str): Name of the database file.

    Returns:
        list: List of complete article dictionaries.
    """

    logger.info("Fetching top 10 news articles from the database")

    connection = None
    articles_selected = []
    try:
        connection = sqlite3.connect(name_db)
        cursor = connection.cursor()

        for item in news_top:
            cursor.execute(
                """
                SELECT id, title, description, content
                FROM articles
                WHERE id = ?
                """,
                (item["id"],),
            )

            row = cursor.fetchone()

            if row:
                articles_selected.append(
                    {
                        "rank": item["rank"],
                        "reason": item["reason"],
                        "id": row[0],
                        "title": row[1],
                        "description": row[2],
                        "content": row[3],
                    }
                )

        logger.info("Raw Top 10 Articles - \n %s" % articles_selected)
        return articles_selected

    except Exception as e:
        logger.exception(f"Failed to fetch article details: {e}")
        raise
    finally:
        if connection:
            connection.close()


def summarize_articles(articles_selected: list) -> dict:
    """Generate concise, rewritten versions of each selected article.

    Args:
        articles_selected (list): Complete article objects.

    Returns:
        dict: Dictionary of summarized articles keyed by title.
    """

    logger.info("Rephrasing the article")

    articles_rephrased = {}

    for article in articles_selected:
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "user",
                        "content": prompts.ARTICLE_SUMMARIZATION_PROMPT.replace(
                            "{{ARTICLE}}", str(article)
                        ),
                    }
                ],
                temperature=1,
                max_completion_tokens=1024,
                top_p=1,
                stream=False,
                stop=None,
                response_format={"type": "json_object"},
            )

            content = news_processor.clean_json_string(completion.choices[0].message.content)
            logger.info("Raw Summarized Article : %s" % content)
            article_rephrased = json.loads(content, strict=False)

            if "title" not in article_rephrased:
                logger.error(
                    "Summarized article missing 'title' field, skipping: %s", content
                )
                continue

            if article_rephrased["title"] not in articles_rephrased:
                articles_rephrased[article_rephrased["title"]] = article_rephrased

        except Exception as e:
            logger.error(
                "Failed to summarize article '%s', skipping: %s",
                article.get("title"),
                e,
            )

    return articles_rephrased


def generate_subject_line(articles_summarized: dict) -> dict:
    """Generate an inbox subject line and preheader for today's digest using the LLM.

    Args:
        articles_summarized (dict): Summarized articles keyed by title, in rank order.

    Returns:
        dict: Dictionary with "subject" and "preheader" keys.
    """

    stories = list(articles_summarized.values())

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompts.SUBJECT_LINE_PROMPT.replace(
                    "{{STORIES}}", str(stories)
                ),
            }
        ],
        temperature=1,
        max_completion_tokens=256,
        top_p=1,
        stream=False,
        stop=None,
        response_format={"type": "json_object"},
    )

    content = news_processor.clean_json_string(completion.choices[0].message.content)
    logger.info("Raw Subject Line : %s" % content)
    return json.loads(content, strict=False)


def get_top_news_digest(name_db: str = "news.db") -> dict:
    """Execute the complete news processing pipeline.

    Args:
        name_db (str): SQLite database file name.

    Returns:
        dict: Final summarized news digest.
    """

    logger.info("=" * 60)
    logger.info("Starting LLM News Pipeline")
    logger.info("=" * 60)

    # Stage 1: Load article titles
    logger.info("[Stage 1] Loading article titles from the database...")
    titles_article = fetch_article_titles(name_db)
    logger.info("[Stage 1] Loaded %d article titles.", len(titles_article))

    # Stage 2: Select top news
    logger.info("[Stage 2] Selecting the top 10 news stories using the LLM...")
    news_top_raw = rank_top_news_articles(titles_article)
    news_top = json.loads(news_processor.clean_json_string(news_top_raw), strict=False)
    if isinstance(news_top, dict):
        for val in news_top.values():
            if isinstance(val, list):
                news_top = val
                break
    logger.info("[Stage 2] Successfully selected %d news stories.", len(news_top))

    # Stage 3: Load complete articles
    logger.info("[Stage 3] Fetching complete article details...")
    articles_selected = fetch_article_details(news_top, name_db)
    logger.info("[Stage 3] Retrieved %d complete articles.", len(articles_selected))

    # Stage 4: Generate summaries
    logger.info("[Stage 4] Generating concise article summaries...")
    articles_summarized = summarize_articles(articles_selected)
    logger.info("[Stage 4] Generated %d summarized articles.", len(articles_summarized))

    logger.info("=" * 60)
    logger.info("LLM News Pipeline completed successfully.")
    logger.info("=" * 60)

    return articles_summarized
