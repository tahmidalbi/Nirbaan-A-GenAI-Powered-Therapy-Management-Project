import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings


def send_invite_email(*, recipient_email: str, therapist_name: str, invite_url: str) -> None:
    """
    Sends a patient invitation email using the configured SMTP credentials.
    Raises RuntimeError if SMTP is not configured.
    Raises smtplib.SMTPException on delivery failure.
    """
    if not settings.SMTP_EMAIL or not settings.SMTP_PASSWORD:
        raise RuntimeError(
            "Email sending is not configured. "
            "Set SMTP_EMAIL and SMTP_PASSWORD in your .env file."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Your Nirbaan therapy invitation from {therapist_name}"
    msg["From"]    = settings.SMTP_EMAIL
    msg["To"]      = recipient_email

    plain = f"""\
You have been invited to join Nirbaan by {therapist_name}.

Click the link below to create your account:
{invite_url}

This link expires in 7 days and can only be used once.
If you did not expect this invitation, you can safely ignore this email.
"""

    html = f"""\
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f0f4f4;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 16px;">
      <table width="520" cellpadding="0" cellspacing="0"
             style="background:#112929;border-radius:12px;overflow:hidden;">
        <tr>
          <td style="background:#0d2525;padding:28px 32px;text-align:center;">
            <h1 style="color:#4ecdc4;margin:0;font-size:1.6rem;letter-spacing:1px;">
              Nirbaan
            </h1>
            <p style="color:#8aa8a8;margin:4px 0 0;font-size:0.85rem;">
              AI-Powered Therapy Platform
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <h2 style="color:#e0e0e0;margin:0 0 16px;">
              You have been invited
            </h2>
            <p style="color:#b0c8c8;line-height:1.6;margin:0 0 24px;">
              Your therapist <strong style="color:#4ecdc4;">{therapist_name}</strong>
              has invited you to create your account on Nirbaan, where you can
              access AI-guided therapy support between your sessions.
            </p>
            <div style="text-align:center;margin:0 0 28px;">
              <a href="{invite_url}"
                 style="display:inline-block;background:#4ecdc4;color:#0a1f1f;
                        padding:14px 36px;border-radius:8px;text-decoration:none;
                        font-weight:700;font-size:1rem;">
                Create My Account
              </a>
            </div>
            <p style="color:#6a9898;font-size:0.8rem;margin:0;">
              This link expires in <strong>7 days</strong> and can only be used once.<br>
              If you did not expect this invitation, you can safely ignore this email.
            </p>
          </td>
        </tr>
        <tr>
          <td style="background:#0d2525;padding:16px 32px;text-align:center;">
            <p style="color:#4a7070;font-size:0.75rem;margin:0;">
              Nirbaan · Khulna University of Engineering &amp; Technology
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
        smtp.sendmail(settings.SMTP_EMAIL, recipient_email, msg.as_string())
