import sys
import io
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from license import create_license
from stripe_handler import send_license_email

def generate_free_key(email="free-user@example.com"):
    # create_license は内部で新しいキーを生成し、データベースに登録します
    new_key = create_license(email)
    print("=========================================")
    print("🆓 無料ライセンスキーを発行しました 🆓")
    print(f"メールアドレス: {email}")
    print(f"ライセンスキー: {new_key}")
    print("=========================================")
    print("※このキーはStripe決済を経由していませんが、即座に「ClearCut」上で制限解除に使えます。")
    print("※Google Spreadsheetにも登録を試みています...")
    
    # GAS Webhookに送信してスプレッドシートへの記録とメール送信を実行する
    send_license_email(email, new_key)
    print("=========================================")

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "free-user@example.com"
    generate_free_key(email)
