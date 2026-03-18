import os
import stripe
from license import create_license

# Load from environment dynamically inside functions
GAS_WEBHOOK_URL = os.getenv("GAS_WEBHOOK_URL", "https://script.google.com/macros/s/AKfycbzmBWscXUWg2OgvDKwe8jZE84mYh93ufXMJp368MRcex8I7-R3qRiAbbeii_ARUQg5e2A/exec")


def create_checkout_session(success_url: str, cancel_url: str, client_reference_id: str = None) -> str:
    """Create a Stripe Checkout session and return the URL."""
    api_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    price_id = os.getenv("STRIPE_PRICE_ID", "").strip()

    if not api_key or not price_id:
        print("[ClearCut] Error: Stripe API Key or Price ID is missing.")
        raise ValueError("Stripe not configured")

    stripe.api_key = api_key

    try:
        session = stripe.checkout.Session.create(
            line_items=[{"price": price_id, "quantity": 1}],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=client_reference_id,
        )
        return session.url
    except Exception as e:
        print(f"[ClearCut] Stripe Checkout Error: {e}")
        raise e


def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """
    Handle Stripe webhook event.
    Returns {"license_key": str, "email": str} on success.
    """
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "").strip()

    event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        
        # ▼▼▼ 新規追加: AI Subtitleからの通知を完全に無視するためのストッパー ▼▼▼
        # AI Subtitleは「Payment Link（固定URL）」を使っています。
        # ClearCutは「アプリ本体から動的にCheckout画面を生成」して動作しています。
        # そのため、Stripeから送られてきたデータに「Payment Link」の痕跡が含まれていれば、
        # それは100%AI Subtitleの購入なので、ここで処理を終了させます。
        if session.get("payment_link"):
            print("[ClearCut] Ignored Payment Link checkout (belongs to AI Subtitle).")
            return {}
        # ▲▲▲ ここまで ▲▲▲

        email = session.get("customer_email") or session.get("customer_details", {}).get("email", "unknown@example.com")
        license_key = session.get("client_reference_id")


        if license_key:
            from database import get_db
            try:
                conn = get_db()
                conn.execute("INSERT INTO licenses (license_key, email) VALUES (?, ?)", (license_key, email))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[ClearCut] Error saving specific license: {e}")
        else:
            # Fallback if no client_reference_id
            license_key = create_license(email)

        # Send email and save to DB via GAS Webhook
        send_license_email(email, license_key)

        print(f"[ClearCut] License issued: {license_key} for {email}")
        return {"license_key": license_key, "email": email}

    return {}


def send_license_email(to_email: str, license_key: str):
    """Send license key to the GAS Webhook to handle email delivery and DB storage."""
    if not GAS_WEBHOOK_URL:
        print(f"[ClearCut] GAS Webhook not configured. License for {to_email}: {license_key}")
        return

    try:
        import urllib.request
        import json
        
        data = json.dumps({
            "type": "license",
            "email": to_email,
            "license_key": license_key
        }).encode("utf-8")
        
        req = urllib.request.Request(
            GAS_WEBHOOK_URL, 
            data=data, 
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req) as response:
            result = response.read().decode("utf-8")
            print(f"[ClearCut] GAS Webhook Response: {result}")
            
    except Exception as e:
        print(f"[ClearCut] Failed to send to GAS Webhook: {e}")
        print(f"[ClearCut] Backup License info for {to_email}: {license_key}")
