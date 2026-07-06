import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def clean_news_data(news):
    """
    Helps in cleaning the news data

    Args:
        news (list): List of news articles

    Returns:
        list: List of cleaned news articles
    """

    news_data = []
    try:
        for article in news:
            title = article.get("title")
            content = article.get("content")
            if not title or not content or "[Removed]" in title:
                continue
            news_data.append(
                {
                    "title": title,
                    "description": article.get("description"),
                    "content": content,
                }
            )
    except Exception as e:
        logger.exception("Failed to clean news data")
        raise

    return news_data


def clean_json_string(text: str) -> str:
    """
    Cleans markdown code block wraps (like ```json ... ```) from LLM output.
    """
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
