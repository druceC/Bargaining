import os
import json
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Load credentials (for Heroku: from env var, for local: from file)
if 'GOOGLE_CREDENTIALS' in os.environ:
    creds_info = json.loads(os.environ['GOOGLE_CREDENTIALS'])
    creds = service_account.Credentials.from_service_account_info(
        creds_info, scopes=['https://www.googleapis.com/auth/drive']
    )
else:
    creds = service_account.Credentials.from_service_account_file(
        'service_account.json', scopes=['https://www.googleapis.com/auth/drive']
    )

service = build('drive', 'v3', credentials=creds)

# Replace this with your actual Drive folder ID
GOOGLE_DRIVE_FOLDER_ID = '1JerKHNql1rE79-ZBNf52q1N9GhtUTyii'

def upload_csv(file_path: Path, file_name: str):
    if not file_path.exists():
        print(f"⚠️ File not found: {file_path}")
        return

    file_metadata = {
        'name': file_name,
        'parents': [GOOGLE_DRIVE_FOLDER_ID]
    }

    media = MediaFileUpload(file_path, mimetype='text/csv')
    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    print(f"✅ Uploaded {file_name} → Drive ID: {uploaded.get('id')}")
