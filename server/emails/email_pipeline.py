import os
import resend
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

resend.api_key = os.getenv("RESEND_API_KEY")


def build_news_cards(summarized_articles):
    cards = ""

    for index, article in enumerate(summarized_articles.values(), start=1):
        cards += f"""
        <div class="card">
            <h2>{article['title']}</h2>
            <p>{article['summary']}</p>
        </div>
        """

    return cards


def build_email_html(summarized_articles):
    template_path = Path(__file__).parent / "template.html"

    with open(template_path, "r", encoding="utf-8") as file:
        html = file.read()

    html = html.replace("{{DATE}}", datetime.now().strftime("%d %B %Y"))

    html = html.replace("{{NEWS_CONTENT}}", build_news_cards(summarized_articles))

    return html


def send_newsletter(receiver_email: str, summarized_articles):
    html = build_email_html(summarized_articles)

    resend.Emails.send(
        {
            "from": "The Morning Brief <onboarding@resend.dev>",
            "to": receiver_email,
            "subject": "📰 The Morning Brief",
            "html": html,
        }
    )


def email_service_pipeline(summarized_articles):
    """ """

    try:
        send_newsletter("chaitanyarudraraju5210@gmail.com", summarized_articles)
    except Exception as e:
        logger.exception("Email pipeline Failed with Exception")
        raise
