"""Agent 6: Notifier — sends email digest of applications."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from loguru import logger
from config.settings import settings
from typing import List, Dict
from datetime import datetime


EMAIL_TEMPLATE = """
<html><body>
<h2>🤖 AutoApply Daily Report — {date}</h2>
<p>Here's your job application summary for today:</p>

<h3>📊 Stats</h3>
<ul>
  <li>Jobs Found: <b>{total_found}</b></li>
  <li>Jobs Scored ≥ 70: <b>{total_eligible}</b></li>
  <li>Applications Submitted: <b>{total_applied}</b></li>
  <li>Applications Failed: <b>{total_failed}</b></li>
</ul>

<h3>✅ Applied Jobs</h3>
<table border="1" cellpadding="8" style="border-collapse:collapse">
  <tr><th>Job Title</th><th>Company</th><th>Score</th><th>Link</th></tr>
  {rows}
</table>
</body></html>
"""


def send_email_digest(jobs_applied: List[Dict], stats: Dict):
    """Send HTML email digest of applied jobs."""
    if not settings.smtp_user or not settings.notify_email:
        logger.warning("Email not configured — skipping notification")
        return

    rows = "".join(
        f"<tr><td>{j['job_title']}</td><td>{j['company']}</td>"
        f"<td>{j.get('score', 'N/A')}</td>"
        f"<td><a href='{j['job_url']}'>View</a></td></tr>"
        for j in jobs_applied
    )

    html_body = EMAIL_TEMPLATE.format(
        date=datetime.now().strftime("%B %d, %Y"),
        total_found=stats.get("total_found", 0),
        total_eligible=stats.get("total_eligible", 0),
        total_applied=stats.get("total_applied", 0),
        total_failed=stats.get("total_failed", 0),
        rows=rows,
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🤖 AutoApply Report — {len(jobs_applied)} Jobs Applied Today"
    msg["From"] = settings.smtp_user
    msg["To"] = settings.notify_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_pass)
            server.sendmail(settings.smtp_user, settings.notify_email, msg.as_string())
        logger.info(f"Email digest sent to {settings.notify_email}")
    except Exception as e:
        logger.error(f"Email send error: {e}")
