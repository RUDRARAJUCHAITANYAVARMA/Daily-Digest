import os

import dotenv
import requests

dotenv.load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")


def get_top_headlines(date: str):
    """Fetch top headlines from the News API.

    Args:
        date (str): Date from which news to be fetched (YYYY-MM-DD).

    Returns:
        list: List of news articles from the specified date.
    """

    response = requests.get(
        f"https://newsapi.org/v2/everything?q=world&from={date}&sortBy=popularity&pageSize=100&apiKey={NEWS_API_KEY}",
        timeout=15,
    )

    if response.status_code == 200:
        return response.json()["articles"]
    else:
        raise Exception(f"Failed to fetch news: {response.json().get('message', 'Unknown error')}")
