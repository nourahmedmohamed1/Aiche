"""
get_google_refresh_token.py — CLI tool to generate Google Drive OAuth 2.0 Refresh Token.

Run from your CLI:
    cd backend
    ..\venv\Scripts\python get_google_refresh_token.py
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]

print("=== GOOGLE DRIVE OAUTH 2.0 REFRESH TOKEN GENERATOR (CLI) ===\n")

client_id = os.getenv("GOOGLE_CLIENT_ID") or input("Enter your Google Client ID: ").strip()
client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or input("Enter your Google Client Secret: ").strip()

if not client_id or not client_secret:
    print("[ERROR] Client ID and Client Secret are required.")
    sys.exit(1)

client_config = {
    "installed": {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

try:
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    print("\nOpening browser for Google Drive authorization...")
    print("Please select your Google Account (e.g. aichecu.webdevelopment@gmail.com) and click ALLOW.\n")

    creds = flow.run_local_server(port=0, prompt="consent")

    refresh_token = creds.refresh_token

    print("=" * 60)
    print("[SUCCESS] GOOGLE REFRESH TOKEN GENERATED!")
    print("=" * 60)
    print(f"\nGOOGLE_CLIENT_ID={client_id}")
    print(f"GOOGLE_CLIENT_SECRET={client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN={refresh_token}\n")

    # Automatically save to .env
    env_file = ".env"
    lines = []
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            lines = [
                line for line in f.readlines()
                if not (
                    line.startswith("GOOGLE_CLIENT_ID=") or
                    line.startswith("GOOGLE_CLIENT_SECRET=") or
                    line.startswith("GOOGLE_REFRESH_TOKEN=")
                )
            ]

    lines.append(f"GOOGLE_CLIENT_ID={client_id}\n")
    lines.append(f"GOOGLE_CLIENT_SECRET={client_secret}\n")
    lines.append(f"GOOGLE_REFRESH_TOKEN={refresh_token}\n")

    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("[OK] Updated your backend/.env file automatically with these credentials!\n")

except Exception as e:
    print(f"\n[ERROR] Authorization failed: {str(e)}")
    print("\nMake sure your OAuth Client ID in Google Cloud Console has:")
    print("  Application type: 'Desktop app' OR Authorized redirect URI: 'http://localhost:8080/'")
