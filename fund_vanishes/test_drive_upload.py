# test_drive_upload.py

from pathlib import Path
from drive_upload import upload_csv

# Point to the test file
test_file = Path(__file__).resolve().parent / 'test_upload.csv'

# Attempt to upload
upload_csv(test_file, 'test_upload.csv')
