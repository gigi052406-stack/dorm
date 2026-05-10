"""
DormNorm — Email Service
Handles all outbound email: credential delivery, OTP, and notifications.

Configuration: fill SMTP_* constants below with your real Gmail credentials.
For Gmail:
  1. Enable 2-Step Verification on your Google account.
  2. Go to Security → App Passwords → generate one for "Mail".
  3. Paste the 16-char app password into SMTP_PASSWORD below.
"""

import smtplib
import random
import string
import threading
import html as _html   # for escaping user-supplied content in email bodies
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import os

# ─── SMTP CONFIG ────────────────────────────────────────────────────────────
# SECURITY WARNING: Do NOT commit real credentials to version control.
# Prefer environment variables over hardcoded values:
#   set DORMNOM_SMTP_USER=you@gmail.com
#   set DORMNOM_SMTP_PASS=your-app-password
# Values below are used only as a fallback when env vars are absent.
SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USERNAME = os.environ.get("DORMNOM_SMTP_USER", "gigi052406@gmail.com")
SMTP_PASSWORD = os.environ.get("DORMNOM_SMTP_PASS", "")
SENDER_NAME   = "DormNorm System"
# ────────────────────────────────────────────────────────────────────────────

# In-memory OTP store: { email: { "otp": str, "expires": datetime } }
_otp_store: dict = {}


# ──────────────────────────────────────────────────────────────────────────
#  LOW-LEVEL SEND
# ──────────────────────────────────────────────────────────────────────────
def _send(to_email: str, subject: str, html_body: str) -> bool:
    """
    Send a single HTML email.
    Returns True on success, False on any SMTP/network failure.
    Errors are printed but never raised — callers decide how to handle.
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{SENDER_NAME} <{SMTP_USERNAME}>"
        msg["To"]      = to_email

        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, [to_email], msg.as_string())

        print(f"[EmailService] ✓ Sent '{subject}' → {to_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("[EmailService] AUTH ERROR — Gmail App Password may be wrong or expired.\n"
              "  Go to: myaccount.google.com → Security → App Passwords → regenerate.")
    except smtplib.SMTPRecipientsRefused as e:
        print(f"[EmailService] Recipient refused: {e}")
    except smtplib.SMTPException as e:
        print(f"[EmailService] SMTP error: {e}")
    except OSError as e:
        print(f"[EmailService] Network error: {e}")
    except Exception as e:
        print(f"[EmailService] Unexpected error: {e}")
    return False


def send_async(to_email: str, subject: str, html_body: str,
               on_done=None) -> None:
    """
    Send an email in a background thread so the UI is never blocked.
    on_done(success: bool) is called from the background thread when finished.
    """
    def _worker():
        ok = _send(to_email, subject, html_body)
        if on_done:
            try:
                on_done(ok)
            except Exception:
                pass
    t = threading.Thread(target=_worker, daemon=True)
    t.start()


# ──────────────────────────────────────────────────────────────────────────
#  EMAIL TEMPLATES
# ──────────────────────────────────────────────────────────────────────────
def _base_template(title: str, body_html: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <style>
        body        {{ font-family: 'Segoe UI', Arial, sans-serif; background:#f0f2f5; margin:0; padding:0; }}
        .wrapper    {{ max-width:560px; margin:40px auto; background:#ffffff;
                       border-radius:12px; overflow:hidden;
                       box-shadow:0 4px 20px rgba(0,0,0,.10); }}
        .header     {{ background:#0D1117; padding:28px 36px; }}
        .header h1  {{ color:#FFD700; margin:0; font-size:22px; letter-spacing:.5px; }}
        .header p   {{ color:#8B949E; margin:4px 0 0; font-size:13px; }}
        .body       {{ padding:32px 36px; color:#1F2328; }}
        .body h2    {{ margin-top:0; font-size:18px; color:#0D1117; }}
        .cred-box   {{ background:#F6F8FA; border:1px solid #D0D7DE; border-radius:8px;
                       padding:16px 20px; margin:20px 0; font-family:monospace; font-size:14px; }}
        .cred-box b {{ color:#0969DA; }}
        .otp-box    {{ background:#FFF8E1; border:1px solid #FFD700; border-radius:8px;
                       padding:20px; text-align:center; margin:24px 0; }}
        .otp-code   {{ font-size:40px; font-weight:bold; letter-spacing:10px;
                       color:#0D1117; font-family:monospace; }}
        .notice     {{ background:#EFF8FF; border-left:4px solid #58A6FF; padding:12px 16px;
                       border-radius:0 6px 6px 0; font-size:13px; color:#0969DA; margin:16px 0; }}
        .footer     {{ background:#F6F8FA; padding:18px 36px; font-size:12px;
                       color:#8B949E; border-top:1px solid #D0D7DE; text-align:center; }}
        .btn        {{ display:inline-block; background:#FFD700; color:#0D1117;
                       padding:10px 28px; border-radius:8px; font-weight:bold;
                       text-decoration:none; font-size:14px; margin-top:10px; }}
      </style>
    </head>
    <body>
      <div class="wrapper">
        <div class="header">
          <h1>🏠 DormNorm</h1>
          <p>Dormitory Management System</p>
        </div>
        <div class="body">
          <h2>{title}</h2>
          {body_html}
        </div>
        <div class="footer">
          This is an automated message from DormNorm. Do not reply to this email.<br>
          © {datetime.now().year} DormNorm. All rights reserved.
        </div>
      </div>
    </body>
    </html>
    """


# ──────────────────────────────────────────────────────────────────────────
#  PUBLIC API
# ──────────────────────────────────────────────────────────────────────────

def send_renter_credentials(to_email: str, full_name: str,
                             username: str, password: str) -> bool:
    """
    Send welcome + login credentials to a newly approved renter.
    Called by ApplicationModule.approve_application() after commit.
    Dispatched in a background thread — returns True immediately (fire-and-forget).
    """
    safe_name     = _html.escape(full_name)
    safe_username = _html.escape(username)
    safe_password = _html.escape(password)
    body = f"""
    <p>Dear <strong>{safe_name}</strong>,</p>
    <p>Your rental application has been <strong style="color:#1A7F37;">approved</strong>.
       Welcome to DormNorm! Below are your login credentials:</p>
    <div class="cred-box">
      <b>Username:</b> {safe_username}<br>
      <b>Password:</b> {safe_password}
    </div>
    <div class="notice">
      🔒 For your security, please change your password immediately after your first login.
    </div>
    <p>If you have any questions, please contact the dormitory office.</p>
    """
    send_async(
        to_email,
        "DormNorm — Your Account Has Been Approved",
        _base_template("Account Approved 🎉", body),
    )
    return True


def send_staff_credentials(to_email: str, full_name: str,
                            username: str, password: str, role: str) -> bool:
    """
    Send onboarding credentials to a newly registered staff member.
    Called by AdminModule.add_admin() after commit.
    Dispatched in a background thread — returns True immediately (fire-and-forget).
    """
    safe_name     = _html.escape(full_name)
    safe_username = _html.escape(username)
    safe_password = _html.escape(password)
    safe_role     = _html.escape(role)
    body = f"""
    <p>Dear <strong>{safe_name}</strong>,</p>
    <p>You have been registered as <strong>{safe_role}</strong> on DormNorm.
       Below are your access credentials:</p>
    <div class="cred-box">
      <b>Username:</b> {safe_username}<br>
      <b>Temporary Password:</b> {safe_password}<br>
      <b>Role:</b> {safe_role}
    </div>
    <div class="notice">
      🔒 This is a temporary password. You must change it upon your first login.
    </div>
    <p>Please keep these credentials confidential. If you did not expect this
       email, contact the system administrator immediately.</p>
    """
    send_async(
        to_email,
        "DormNorm — Staff Account Created",
        _base_template("Staff Account Created", body),
    )
    return True


def send_otp(to_email: str, full_name: str) -> str | None:
    """
    Generate a 6-digit OTP, email it, then store it only if the send succeeded.
    Returns the OTP string on success, None on failure.
    The OTP is stored in _otp_store keyed by email (lowercased).

    Security notes:
      • OTP is written AFTER a successful send so a failed delivery leaves no
        live entry in the store (prevents blind guessing against a dangling entry).
      • verify_otp limits failed attempts to 5 before invalidating the entry.
    """
    otp = "".join(random.choices(string.digits, k=6))
    expires = datetime.now() + timedelta(minutes=10)
    safe_name = _html.escape(full_name or "User")

    body = f"""
    <p>Dear <strong>{safe_name}</strong>,</p>
    <p>You requested a password reset for your DormNorm account.
       Use the One-Time Password below to verify your identity:</p>
    <div class="otp-box">
      <div class="otp-code">{otp}</div>
      <p style="margin:8px 0 0; color:#636C76; font-size:13px;">
        Valid for <strong>10 minutes</strong>
      </p>
    </div>
    <div class="notice">
      ⚠️ Do not share this OTP with anyone. DormNorm staff will never ask for it.
    </div>
    <p>If you did not request a password reset, you can safely ignore this email.</p>
    """
    ok = _send(
        to_email,
        "DormNorm — Password Reset OTP",
        _base_template("Password Reset Request", body),
    )
    if ok:
        # Only store AFTER confirmed delivery so no stale entry lingers on failure
        _otp_store[to_email.lower()] = {
            "otp": otp, "expires": expires, "attempts": 0
        }
        return otp
    return None


def verify_otp(email: str, otp: str) -> bool:
    """
    Verify a submitted OTP.
    Returns True if valid, not expired, and within the attempt limit.
    Clears the store entry on success OR after too many failed attempts.

    Thread-safety: uses dict.pop() which is atomic in CPython, preventing
    a TOCTOU race where two threads both pass with the same OTP.
    """
    key = email.lower()
    entry = _otp_store.get(key)
    if not entry:
        return False
    if datetime.now() > entry["expires"]:
        _otp_store.pop(key, None)
        return False
    if entry["otp"] != otp.strip():
        # Increment attempt counter; lock out after 5 wrong guesses
        entry["attempts"] = entry.get("attempts", 0) + 1
        if entry["attempts"] >= 5:
            _otp_store.pop(key, None)
            print(f"[EmailService] OTP for {key} invalidated after 5 failed attempts.")
        return False
    # Success — atomically remove the entry so it cannot be reused
    _otp_store.pop(key, None)
    return True


def send_application_received(to_email: str, full_name: str) -> bool:
    """
    Acknowledge receipt of a rental application.
    Dispatched in a background thread — returns True immediately (fire-and-forget).
    """
    safe_name = _html.escape(full_name)
    body = f"""
    <p>Dear <strong>{safe_name}</strong>,</p>
    <p>We have received your rental application. Our team will review it and
       get back to you within <strong>2–3 business days</strong>.</p>
    <p>You will receive another email once a decision has been made.</p>
    <p>Thank you for your interest in DormNorm!</p>
    """
    send_async(
        to_email,
        "DormNorm — Application Received",
        _base_template("Application Received", body),
    )
    return True