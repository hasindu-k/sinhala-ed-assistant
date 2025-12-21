import uuid
from typing import Optional
from app.core.firebase import get_bucket


def upload_audio_to_firebase(local_path: str) -> Optional[str]:
    try:
        bucket = get_bucket()
    except Exception as e:
        print(f"[audio_storage] Firebase not initialized: {e}")
        return None

    filename = f"{uuid.uuid4()}.wav"
    blob_path = f"voice_messages/{filename}"

    blob = bucket.blob(blob_path)

    try:
        blob.upload_from_filename(local_path, content_type="audio/wav")
        return f"gs://{bucket.name}/{blob_path}"
    except Exception as e:
        print(f"[audio_storage] upload failed: {e}")
        return None
