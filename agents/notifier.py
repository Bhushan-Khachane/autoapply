"""Agent 6: Notifier — sends HTML email digest of applications."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from loguru import logger
from config.settings import settings
from typing import List, Dict
from datetime import datetime

SMTP_TIMEOUT = 30  # seconds

EMAIL_TEMPLATE = """
<html>
<head><style>
  body {{ font-family: Arial, sans-serif; color: #333; }}
  h2 {{ color: #2c3e50; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th {{ background-color: #2c3e50; color: white; padding: 10px; text-align: left; }}
  td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
  tr:hover {{ background-color: #f5f5f5; }}
  .stat {{ font-size: 18px; font-weight: bold; color: #2980b9; }}
</style></head>
<body>
<h2>🤖 AutoApply Daily Report — {date}</h2>
<p>Here's your job application summary:</p>

<h3>📊 Stats</h3>
<ul>
  <li>Jobs Found: <span class="stat">{total_found}</span></li>
  <li>Jobs Scored ≥ {min_score}: <span class="stat">{total_eligible}</span></li>
  <li>Applications Submitted: <span class="stat">{total_applied}</span></li>
  <li>Applications Failed: <span class="stat">{total_failed}</span></li>
</ul>

<h3>✅ Applied Jobs</h3>
<table>
  <tr><th>Job Title</th><th>Company</th><th>Location</th><th>Score</th><th>Link</th></tr>
  {rows}
</table>
</body></html>
"""


def send_email_digest(jobs_applied: List[Dict], stats: Dict) -> bool:
    """Send HTML email digest. Returns True on success, False on failure."""
    if not settings.smtp_user or not settings.notify_email:
        logger.warning("Email not configured (SMTP_USER / NOTIFY_EMAIL missing) — skipping notification")
        return False

    if not jobs_applied:
        logger.info("No jobs applied — skipping email digest")
        return False

    rows = "".join(
        f"<tr>"
        f"<td>{j.get('job_title', '')}</td>"
        f"<td>{j.get('company', '')}</td>"
        f"<td>{j.get('location', '')}</td>"
        f"<td><b>{j.get('score', 'N/A')}</b></td>"
        f"<td><a href='{j.get('job_url', '#')}'>View Job</a></td>"
        f"</tr>"
        for j in jobs_applied
    )

    html_body = EMAIL_TEMPLATE.format(
        date=datetime.now().strftime("%B %d, %Y at %I:%M %p"),
        min_score=stats.get("min_score", 70),
        total_found=stats.get("total_found", 0),
        total_eligible=stats.get("total_eligible", 0),
        total_applied=stats.get("total_applied", 0),
        total_failed=stats.get("total_failed", 0),
        rows=rows,
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🤖 AutoApply Report — {len(jobs_applied)} Jobs Applied | {datetime.now().strftime('%b %d')}"
    msg["From"] = settings.smtp_user
    msg["To"] = settings.notify_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=SMTP_TIMEOUT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.smtp_user, settings.smtp_pass)
            server.sendmail(settings.smtp_user, settings.notify_email, msg.as_string())
        logger.info(f"📧 Email digest sent to {settings.notify_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed — check SMTP_USER and SMTP_PASS in .env")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
    except Exception as e:
        logger.error(f"Email send error: {e}")
    return False
