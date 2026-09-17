import base64
import json
import logging
import os
import re

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]


def _parse_credentials(creds_input: str) -> dict:
    """
    Parses Google Service Account credentials flexibly.
    Supports:
    - Raw JSON string
    - Base64-encoded JSON string
    - Path to a .json key file
    - Auto-repair for unescaped newlines in .env files
    """
    if not creds_input:
        raise ValueError("Credentials string is empty")

    raw = creds_input.strip()

    # 1. If string is a file path to an existing JSON file
    if os.path.isfile(raw):
        with open(raw, "r", encoding="utf-8") as f:
            return json.load(f)

    # 2. If Base64 encoded (strips single or double quotes wrapper if present)
    if raw.startswith("'") and raw.endswith("'"):
        raw = raw[1:-1].strip()
    elif raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1].strip()

    if not raw.startswith("{"):
        try:
            decoded = base64.b64decode(raw).decode("utf-8").strip()
            if decoded.startswith("{"):
                raw = decoded
        except Exception:
            pass

    # 3. Direct JSON parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 4. Auto-repair unescaped newlines in private keys
    try:
        cleaned = raw.replace("\r\n", "\n")
        cleaned = re.sub(r"(?<!\\)\n", r"\\n", cleaned)
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid GOOGLE_DRIVE_CREDENTIALS JSON format: {str(e)}. "
            "Tip: You can Base64-encode your Google Service Account JSON key to prevent quote and newline syntax errors in .env!"
        ) from e


def upload_to_drive(file_path: str, filename: str) -> str:
    """
    Uploads a file to Google Drive, makes it publicly viewable,
    and returns its shareable URL.

    Requirements:
    - GOOGLE_DRIVE_CREDENTIALS: JSON string, Base64 string, or path to JSON file
    - GOOGLE_DRIVE_FOLDER_ID: Optional target folder ID in AIChE Google Drive
    """
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    creds_json = os.getenv("GOOGLE_DRIVE_CREDENTIALS") or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

    if not creds_json and not (refresh_token and client_id and client_secret):
        logger.warning("GOOGLE_DRIVE_CREDENTIALS / OAuth tokens not set. Falling back to local static path.")
        return f"/static/certificates/{filename}"

    try:
        from google.oauth2 import service_account
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        if refresh_token and client_id and client_secret:
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=SCOPES,
            )
        else:
            info = _parse_credentials(creds_json)
            credentials = service_account.Credentials.from_service_account_info(
                info, scopes=SCOPES
            )

        service = build("drive", "v3", credentials=credentials)

        file_metadata = {"name": filename}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        mimetype = "application/pdf" if filename.lower().endswith(".pdf") else "image/png"
        media = MediaFileUpload(file_path, mimetype=mimetype, resumable=True)

        drive_file = (
            service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink",
                supportsAllDrives=True,
            )
            .execute()
        )

        file_id = drive_file.get("id")

        # Set permission: Anyone with link can view
        service.permissions().create(
            fileId=file_id,
            body={"role": "reader", "type": "anyone"},
            supportsAllDrives=True,
        ).execute()

        # Shareable view URL
        shareable_url = f"https://drive.google.com/uc?export=view&id={file_id}"
        return shareable_url

    except Exception as e:
        err_msg = str(e)
        if "storageQuotaExceeded" in err_msg or "Service Accounts do not have storage quota" in err_msg:
            logger.warning(
                f"Google Drive upload skipped for {filename}: Service accounts cannot upload directly into personal @gmail.com folders without a Shared Drive. "
                "Falling back to local static URL."
            )
            return f"/static/certificates/{filename}"

        logger.error(f"Failed to upload {filename} to Google Drive: {err_msg}")
        raise RuntimeError(f"Google Drive upload failed: {err_msg}") from e
