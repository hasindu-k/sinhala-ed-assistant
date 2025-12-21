import os
import uuid
from typing import Optional

from app.core.firebase import get_bucket


def upload_audio_to_firebase(local_path: str, session_id: str) -> Optional[str]:
    """Upload a local audio file to Firebase Storage and return a public URL.

    File is stored at: voice_messages/<session_id>/<uuid>.wav
    Returns the public URL or None on failure.
    """
    try:
        bucket = get_bucket()
    except Exception as e:
        print(f"[audio_storage] Firebase not initialized: {e}")
        return None

    filename = f"{uuid.uuid4()}.wav"
    blob_path = f"voice_messages/{session_id}/{filename}"
    blob = bucket.blob(blob_path)

    try:
        blob.upload_from_filename(local_path, content_type="audio/wav")
        # Make public so frontend can fetch directly (may be optional)
        try:
            blob.make_public()
            return blob.public_url
        except Exception:
            # If making public fails (security rules), return signed URL or storage path
            return f"gs://{bucket.name}/{blob_path}"
    except Exception as e:
        print(f"[audio_storage] upload failed: {e}")
        return None
