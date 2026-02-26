import os
import stripe
from license import create_license

# Load from environment
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "noreply@clearcut.app")


def create_checkout_session(success_url: str, cancel_url: str) -> str:
    """Create a Stripe Checkout session and return the URL."""
    if not stripe.api_key or not STRIPE_PRICE_ID:
        raise ValueError("Stripe not configured")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return session.url


def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """
    Handle Stripe webhook event.
    Returns {"license_key": str, "email": str} on success.
    """
    event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        email = session.get("customer_email") or session.get("customer_details", {}).get("email", "unknown@example.com")

        # Generate license
        license_key = create_license(email)

        # Send email (if SendGrid configured)
        send_license_email(email, license_key)

        print(f"[ClearCut] License issued: {license_key} for {email}")
        return {"license_key": license_key, "email": email}

    return {}


def send_license_email(to_email: str, license_key: str):
    """Send license key via email. Falls back to console output if SendGrid not configured."""
    if not SENDGRID_API_KEY:
        print(f"[ClearCut] Email not configured. License for {to_email}: {license_key}")
        return

    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail

        sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
        message = Mail(
            from_email=SENDGRID_FROM_EMAIL,
            to_emails=to_email,
            subject="Your ClearCut Pro License Key",
            plain_text_content=f"""Thank you for upgrading to ClearCut Pro.

Your License Key:

{license_key}

Enter this key in ClearCut to unlock unlimited access.

— ClearCut
Simple. Fast. Just works.""",
        )
        sg.send(message)
        print(f"[ClearCut] License email sent to {to_email}")
    except Exception as e:
        print(f"[ClearCut] Failed to send email: {e}")
        print(f"[ClearCut] License for {to_email}: {license_key}")
