import datetime
import hashlib
import hmac
import html
import logging
import os
import pathlib
from urllib.parse import quote

import dotenv
import requests
import resend

from models import news_fetcher

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

resend.api_key = os.getenv("RESEND_API_KEY")
UNSUBSCRIBE_SECRET = os.getenv("UNSUBSCRIBE_SECRET")
UNSUBSCRIBE_BASE_URL = os.getenv(
    "UNSUBSCRIBE_BASE_URL", "https://daily-digest-subscribe.chaitanyarudraraju5210.workers.dev"
)

DEFAULT_SUBJECT = "📰 Daily Digest"


def build_unsubscribe_url(email: str) -> str:
    """Build a signed, one-click unsubscribe link for a recipient.

    The token is an HMAC-SHA256 of the email keyed by UNSUBSCRIBE_SECRET, verified
    by the Cloudflare Worker without needing any server-side storage.

    Args:
        email (str): Recipient email address.

    Returns:
        str: URL that unsubscribes the recipient when opened.
    """

    token = hmac.new(UNSUBSCRIBE_SECRET.encode(), email.encode(), hashlib.sha256).hexdigest()
    return f"{UNSUBSCRIBE_BASE_URL}/unsubscribe?email={quote(email)}&token={token}"


def build_news_cards(articles_summarized: dict) -> str:
    """Build the HTML cards for the summarized articles.

    Args:
        articles_summarized (dict): Dictionary of summarized articles.

    Returns:
        str: HTML string containing cards for each article.
    """

    stories = list(articles_summarized.values())
    cards = ""
    for index, article in enumerate(stories, start=1):
        divider = ""
        if index != len(stories):
            divider = """
      <tr><td colspan="2" class="dd-divider" style="padding-top:22px;"><table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"><tr><td height="1" style="background-color:#e0ddd3; font-size:1px; line-height:1px;">&nbsp;</td></tr></table></td></tr>"""

        cards += f"""
    <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0" style="margin:0 0 28px 0;">
      <tr>
        <td width="40" valign="top" class="dd-num" style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif; font-size:20px; line-height:1.3; font-weight:700; color:#b5502e; padding-right:12px;">{index:02d}</td>
        <td valign="top">
          <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
            <tr><td class="dd-headline" style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif; font-size:18px; line-height:1.35; font-weight:700; color:#1e2b23;">{html.escape(article['title'])}</td></tr>
            <tr><td class="dd-summary" style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif; font-size:15px; line-height:1.6; color:#3f473f; padding-top:6px; mso-line-height-rule:exactly;">{html.escape(article['summary'])}</td></tr>
          </table>
        </td>
      </tr>{divider}
    </table>
        """

    return cards


def build_email_html(articles_summarized: dict, preheader: str, unsubscribe_url: str) -> str:
    """Construct the complete newsletter HTML content using a template file.

    Args:
        articles_summarized (dict): Dictionary of summarized articles.
        preheader (str): Short preview text shown next to the subject in inboxes.
        unsubscribe_url (str): Signed link that unsubscribes the recipient.

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
    content_html = content_html.replace("{{UNSUBSCRIBE_URL}}", unsubscribe_url)

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

    unsubscribe_url = build_unsubscribe_url(email_receiver)
    html_content = build_email_html(articles_summarized, preheader, unsubscribe_url)

    resend.Emails.send(
        {
            "from": "Daily Digest <newsletter@dailydigest.in>",
            "to": email_receiver,
            "subject": subject,
            "html": html_content,
            "headers": {"List-Unsubscribe": f"<{unsubscribe_url}>"},
        }
    )


def email_service_pipeline(articles_summarized: dict):
    """Execute the email sending pipeline to dispatch the daily newsletter.

    Args:
        articles_summarized (dict): Dictionary of summarized articles.
    """

    try:
        audience_id = os.getenv("RESEND_AUDIENCE_ID")
        if not audience_id:
            raise ValueError("RESEND_AUDIENCE_ID environment variable is not set")
        if not UNSUBSCRIBE_SECRET:
            raise ValueError("UNSUBSCRIBE_SECRET environment variable is not set")

        logger.info("Fetching subscriber emails from Resend audience...")
        response = requests.get(
            f"https://api.resend.com/audiences/{audience_id}/contacts",
            headers={"Authorization": f"Bearer {resend.api_key}"},
            timeout=15,
        )
        response.raise_for_status()

        data = response.json()
        emails = [
            contact["email"]
            for contact in data.get("data", [])
            if not contact.get("unsubscribed")
        ]
        logger.info(f"Retrieved {len(emails)} active subscriber(s).")

        if not emails:
            logger.info("No active subscribers to send the newsletter to.")
            return

        try:
            subject_line = news_fetcher.generate_subject_line(articles_summarized)
            subject = f"📰 Daily Digest: {subject_line['subject']}"
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
