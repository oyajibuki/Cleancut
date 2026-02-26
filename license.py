import secrets
import string
from datetime import datetime, date

from database import get_db

FREE_DAILY_LIMIT = 3


def generate_license() -> str:
    """Generate a license key in CC-XXXX-XXXX-XXXX-XXXX format."""
    chars = string.ascii_uppercase + string.digits
    segments = [
        "".join(secrets.choice(chars) for _ in range(4))
        for _ in range(4)
    ]
    return f"CC-{'-'.join(segments)}"


def create_license(email: str) -> str:
    """Create a new license key and store it in DB."""
    key = generate_license()
    conn = get_db()
    conn.execute(
        "INSERT INTO licenses (license_key, email) VALUES (?, ?)",
        (key, email)
    )
    conn.commit()
    conn.close()
    return key


def verify_license(license_key: str) -> bool:
    """Check if a license key is valid and active."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM licenses WHERE license_key = ? AND is_active = 1",
        (license_key,)
    ).fetchone()
    conn.close()

    if row is None:
        return False

    # Check expiry if set
    if row["expires_at"]:
        expires = datetime.fromisoformat(row["expires_at"])
        if datetime.utcnow() > expires:
            return False

    return True


def get_today_usage(ip_address: str) -> int:
    """Get how many times this IP has used the service today."""
    conn = get_db()
    today_str = date.today().isoformat()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM usage_log WHERE ip_address = ? AND DATE(used_at) = ?",
        (ip_address, today_str)
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


def record_usage(ip_address: str):
    """Record a usage event for this IP."""
    conn = get_db()
    conn.execute(
        "INSERT INTO usage_log (ip_address) VALUES (?)",
        (ip_address,)
    )
    conn.commit()
    conn.close()


def can_use(ip_address: str, license_key: str = None) -> dict:
    """
    Check if user can use the service.
    Returns: {"allowed": bool, "is_pro": bool, "used": int, "limit": int}
    """
    # Pro user
    if license_key and verify_license(license_key):
        return {"allowed": True, "is_pro": True, "used": 0, "limit": -1}

    # Free user
    used = get_today_usage(ip_address)
    return {
        "allowed": used < FREE_DAILY_LIMIT,
        "is_pro": False,
        "used": used,
        "limit": FREE_DAILY_LIMIT,
    }
