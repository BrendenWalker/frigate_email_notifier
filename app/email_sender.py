from __future__ import annotations

import logging
import re
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import Config

logger = logging.getLogger(__name__)


def send_alert_email(
    config: Config,
    subject: str,
    snapshot_bytes: bytes,
    event_json: str,
) -> None:
    html_body = (
        "<html><body>"
        "<img src='cid:EmbeddedContent_1' />"
        f"{event_json}"
        "</body></html>"
    )
    plain_body = re.sub(r"<[^>]+?>", "", html_body)

    message = MIMEMultipart("related")
    message["Subject"] = subject
    message["From"] = config.smtp_from
    message["To"] = ", ".join(config.smtp_to)

    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(plain_body, "plain", "utf-8"))
    alternative.attach(MIMEText(html_body, "html", "utf-8"))
    message.attach(alternative)

    image = MIMEImage(snapshot_bytes, _subtype="jpeg")
    image.add_header("Content-ID", "<EmbeddedContent_1>")
    image.add_header("Content-Disposition", "inline", filename="EmbeddedContent_1")
    message.attach(image)

    logger.info("Sending alert email to %s", ", ".join(config.smtp_to))
    with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=30) as client:
        if config.smtp_use_tls:
            client.starttls()
        client.login(config.smtp_user, config.smtp_pass)
        client.sendmail(config.smtp_from, config.smtp_to, message.as_string())
