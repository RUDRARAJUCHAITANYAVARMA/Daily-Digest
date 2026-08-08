# Daily Digest
Daily Digest is an automated daily newsletter that curates and delivers the top 10 most important news stories to all registered users, ensuring they stay informed with concise and relevant updates every day.

## Architecture

```mermaid
flowchart TD
    subgraph Signup["Signup flow"]
        Visitor(["Visitor"]) -->|"enters email"| Site["index.html — GitHub Pages\n(dailydigest.in)"]
        Site -->|"GET count / POST email"| Worker["Cloudflare Worker\ncloudflare-worker/subscribe.js"]
        Worker -->|"add / resubscribe contact"| Audience[("Resend Audience\n(subscriber list)")]
        Worker -->|"send welcome email"| Resend["Resend\n(email API)"]
    end

    subgraph Daily["Daily digest pipeline"]
        Cron["cron-job.org\n(daily @ 02:00 UTC)"] -->|"POST workflow_dispatch"| GHA["GitHub Actions\n.github/workflows/run_pipeline.yml"]
        GHA --> Pipeline["server/pipeline.py"]
        Pipeline --> NewsAPI["News API\nnews/news_api.py"]
        Pipeline --> DB[("SQLite\nnews.db (temp)")]
        Pipeline --> LLM["LLM summarization\nmodels/news_fetcher.py"]
        Pipeline --> EmailPipeline["emails/email_pipeline.py"]
        EmailPipeline -->|"fetch active subscribers"| Audience
        EmailPipeline -->|"send daily digest"| Resend
    end

    Resend -->|"delivers email"| Inbox(["Subscriber inbox"])

    style Audience fill:#f5e6d3,stroke:#8B3A2E
    style Resend fill:#f5e6d3,stroke:#8B3A2E
```

**Signup flow:** a visitor enters their email on the site (hosted on GitHub Pages under `dailydigest.in`), which calls a Cloudflare Worker. The Worker adds the contact to a Resend Audience and sends a personalized welcome email via Resend.

**Daily digest pipeline:** cron-job.org triggers the GitHub Actions workflow once a day (GitHub's own built-in `schedule:` trigger is unreliable, so an external scheduler calls `workflow_dispatch` on the Actions API instead). The workflow runs `pipeline.py`, which fetches the day's headlines, stores them temporarily in SQLite, summarizes the top 10 with an LLM, then emails the digest to every active subscriber pulled from the same Resend Audience.
