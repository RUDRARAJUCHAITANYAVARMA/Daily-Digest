import datetime
import html
import logging
import os
import pathlib

import dotenv
import requests
import resend

from models import news_fetcher

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

resend.api_key = os.getenv("RESEND_API_KEY")

DEFAULT_SUBJECT = "📰 The Morning Brief"


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
            <h2>{html.escape(article['title'])}</h2>
            <p>{html.escape(article['summary'])}</p>
        </div>
        """

    return cards


def build_email_html(articles_summarized: dict, preheader: str) -> str:
    """Construct the complete newsletter HTML content using a template file.

    Args:
        articles_summarized (dict): Dictionary of summarized articles.
        preheader (str): Short preview text shown next to the subject in inboxes.

    Returns:
        str: Complete HTML content for the newsletter.
    """

    path_template = pathlib.Path(__file__).parent / "template.html"

    with open(path_template, "r", encoding="utf-8") as file:
        content_html = file.read()

    current_date = datetime.datetime.now().strftime("%d %B %Y")
    content_html = content_html.replace("{{DATE}}", current_date)
    content_html = content_html.replace(
        "{{NEWS_CONTENT}}", build_news_cards(articles_summarized)
    )
    content_html = content_html.replace("{{PREHEADER_TEXT}}", html.escape(preheader))

    return content_html


def send_newsletter(
    email_receiver: str, articles_summarized: dict, subject: str, preheader: str
):
    """Send the newsletter email to a specified receiver email address.

    Args:
        email_receiver (str): Email address of the recipient.
        articles_summarized (dict): Dictionary of summarized articles.
        subject (str): Subject line for the email.
        preheader (str): Short preview text shown next to the subject in inboxes.
    """

    html_content = build_email_html(articles_summarized, preheader)

    resend.Emails.send(
        {
            "from": "The Morning Brief <newsletter@dailydigest.in>",
            "to": email_receiver,
            "subject": subject,
            "html": html_content,
        }
    )


def email_service_pipeline(articles_summarized: dict):
    """Execute the email sending pipeline to dispatch the daily newsletter.

    Args:
        articles_summarized (dict): Dictionary of summarized articles.
    """

    try:
        sheets_endpoint = os.getenv("SUBSCRIBERS_SHEETS_ENDPOINT")
        if not sheets_endpoint:
            raise ValueError("SUBSCRIBERS_SHEETS_ENDPOINT environment variable is not set")

        logger.info("Fetching subscriber emails from Google Sheet...")
        response = requests.get(f"{sheets_endpoint}?action=getEmails", timeout=15)
        response.raise_for_status()
        
        data = response.json()
        if not data.get("success"):
            raise ValueError(f"Failed to retrieve subscribers: {data.get('message')}")

        emails = data.get("emails", [])
        logger.info(f"Retrieved {len(emails)} active subscriber(s).")

        if not emails:
            logger.info("No active subscribers to send the newsletter to.")
            return

        try:
            subject_line = news_fetcher.generate_subject_line(articles_summarized)
            subject = subject_line["subject"]
            preheader = subject_line["preheader"]
        except Exception as subject_error:
            logger.error(
                f"Failed to generate subject line, using fallback: {subject_error}"
            )
            subject = DEFAULT_SUBJECT
            preheader = ""

        for email in emails:
            try:
                logger.info(f"Sending newsletter to {email}...")
                send_newsletter(email, articles_summarized, subject, preheader)
            except Exception as email_error:
                logger.error(f"Failed to send newsletter to {email}: {email_error}")

    except Exception as e:
        logger.exception(f"Email pipeline Failed with Exception: {e}")
        raise
