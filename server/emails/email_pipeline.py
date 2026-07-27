import datetime
import logging
import os
import pathlib

import dotenv
import resend

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

resend.api_key = os.getenv("RESEND_API_KEY")


def build_news_cards(articles_summarized: dict) -> str:
    """Build the HTML cards for the summarized articles.

    Args:
        articles_summarized (dict): Dictionary of summarized articles.

    Returns:
        str: HTML string containing cards for each article.
    """

    cards = ""
    for article in articles_summarized.values():
        cards += f"""
        <div class="card">
            <h2>{article['title']}</h2>
            <p>{article['summary']}</p>
        </div>
        """

    return cards


def build_email_html(articles_summarized: dict) -> str:
    """Construct the complete newsletter HTML content using a template file.

    Args:
        articles_summarized (dict): Dictionary of summarized articles.

    Returns:
        str: Complete HTML content for the newsletter.
    """

    path_template = pathlib.Path(__file__).parent / "template.html"

    with open(path_template, "r", encoding="utf-8") as file:
        html = file.read()

    current_date = datetime.datetime.now().strftime("%d %B %Y")
    html = html.replace("{{DATE}}", current_date)
    html = html.replace("{{NEWS_CONTENT}}", build_news_cards(articles_summarized))

    return html


def send_newsletter(email_receiver: str, articles_summarized: dict):
    """Send the newsletter email to a specified receiver email address.

    Args:
        email_receiver (str): Email address of the recipient.
        articles_summarized (dict): Dictionary of summarized articles.
    """

    html = build_email_html(articles_summarized)

    resend.Emails.send(
        {
            "from": "The Morning Brief <newsletter@dailydigest.in>",
            "to": email_receiver,
            "subject": "📰 The Morning Brief",
            "html": html,
        }
    )


def email_service_pipeline(articles_summarized: dict):
    """Execute the email sending pipeline to dispatch the daily newsletter.

    Args:
        articles_summarized (dict): Dictionary of summarized articles.
    """

    try:
        send_newsletter("chaitanyarudraraju5210@gmail.com", articles_summarized)
    except Exception as e:
        logger.exception(f"Email pipeline Failed with Exception: {e}")
        raise
