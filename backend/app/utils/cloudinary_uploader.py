import os
import logging
import cloudinary
import cloudinary.uploader

logger = logging.getLogger(__name__)


def upload_to_cloudinary(file_path: str, filename: str) -> str:
    """
    Uploads a file (PNG or PDF certificate) to Cloudinary and returns its secure CDN URL.

    Supported Environment Variables:
    - CLOUDINARY_URL (e.g. "cloudinary://123456789:abcdef@mycloud")
    OR
    - CLOUDINARY_CLOUD_NAME
    - CLOUDINARY_API_KEY
    - CLOUDINARY_API_SECRET
    """
    cloudinary_url = os.getenv("CLOUDINARY_URL")
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")

    if not cloudinary_url and not (cloud_name and api_key and api_secret):
        logger.warning("Cloudinary environment variables not set. Falling back to local static URL.")
        return f"/static/certificates/{filename}"

    try:
        if cloudinary_url:
            cloudinary.config(cloudinary_url=cloudinary_url, secure=True)
        else:
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True,
            )

        public_id = os.path.splitext(filename)[0]

        response = cloudinary.uploader.upload(
            file_path,
            folder="certificates",
            public_id=public_id,
            resource_type="auto",
            overwrite=True,
        )

        secure_url = response.get("secure_url")
        if not secure_url:
            raise ValueError("No secure_url returned by Cloudinary upload response")

        logger.info(f"Successfully uploaded {filename} to Cloudinary: {secure_url}")
        return secure_url

    except Exception as e:
        logger.error(f"Cloudinary upload failed for {filename}: {str(e)}")
        raise RuntimeError(f"Cloudinary upload failed: {str(e)}") from e
