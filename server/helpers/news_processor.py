import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def clean_news_data(news: list) -> list:
    """Clean the raw news data by filtering out removed or incomplete articles.

    Args:
        news (list): List of raw news articles.

    Returns:
        list: List of cleaned news articles.
    """

    try:
        return [
            {
                "title": article.get("title"),
                "description": article.get("description"),
                "content": article.get("content"),
            }
            for article in news
            if article.get("title")
            and article.get("content")
            and "[Removed]" not in article.get("title")
        ]
    except Exception as e:
        logger.exception(f"Failed to clean news data: {e}")
        raise


def clean_json_string(text: str) -> str:
    """Clean markdown code block wraps (like ```json ... ```) from LLM output.

    Args:
        text (str): The raw string response from the LLM.

    Returns:
        str: The cleaned JSON string.
    """

    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
