import requests
import os
from dotenv import load_dotenv

load_dotenv()

news_api_key = os.getenv("NEWS_API_KEY")


def get_top_headlines(date):
    """
    Fetch top headlines from the News API

    Parameters:
        date: date from which news to be fetched (YYYY-MM-DD)

    Returns:
        list: list of news articles from the specified date
    """

    response = requests.get(
        f"https://newsapi.org/v2/everything?q=world&from={date}&sortBy=popularity&pageSize=100&apiKey={news_api_key}"
    )

    if response.status_code == 200:
        return response.json()["articles"]
    else:
        raise Exception(f"Failed to fetch news: {response.json().get('message', 'Unknown error')}")
