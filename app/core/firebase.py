import os
from typing import Optional

import firebase_admin
from firebase_admin import credentials, storage

from config.settings import settings


def init_firebase():
    """Initialize Firebase app and return the storage bucket instance.

    Expects:
      - config/firebase_service_account.json to exist
      - FIREBASE_BUCKET_NAME environment variable set
    """
    if not firebase_admin._apps:
        sa_path = os.getenv("FIREBASE_SERVICE_ACCOUNT", "config/firebase_service_account.json")
        bucket_name = os.getenv("FIREBASE_BUCKET_NAME")
        if not os.path.exists(sa_path):
            raise FileNotFoundError(f"Firebase service account file not found: {sa_path}")

        cred = credentials.Certificate(sa_path)
        firebase_admin.initialize_app(
            cred,
            {"storageBucket": bucket_name} if bucket_name else None
        )


def get_bucket():
    """Return the initialized storage bucket.

    Will initialize firebase if not already initialized.
    """
    if not firebase_admin._apps:
        init_firebase()

    bucket_name = os.getenv("FIREBASE_BUCKET_NAME")
    if bucket_name:
        return storage.bucket(bucket_name)
    return storage.bucket()