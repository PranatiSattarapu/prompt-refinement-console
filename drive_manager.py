from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
import os
import io
import json
import streamlit as st

# ----------------------------------------------------------------------
# 1. Configuration (IDs and Scopes)
# ----------------------------------------------------------------------
FOLDER_ID_PATIENT_DATA = "17CdWnoybK0R7pKsdug7Oxo-Xd4iUVRCX"
FOLDER_ID_GUIDELINES = "1Wj-O-q9MCdYQz4Uo4zkNFtgPexbTj5rn"
FOLDER_ID_PROMPT_FRAMEWORK = "1A8oN2RYZMdOCZRmsC6d1kdyeAjzdzfw1"

SCOPES = ["https://www.googleapis.com/auth/drive"]

# ----------------------------------------------------------------------
# 2. Authentication
# ----------------------------------------------------------------------
def get_drive_service():
    """Loads Google service account from Streamlit Secrets."""
    try:
        service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
        creds = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES
        )
        service = build("drive", "v3", credentials=creds)
        return service
    except Exception as e:
        print(f"Error initializing Google Drive service: {e}")
        return None


# ----------------------------------------------------------------------
# 3. File Listing
# ----------------------------------------------------------------------
def api_get_files_in_folder(service, folder_id):
    """Retrieves metadata for non-trashed files within a specific folder ID."""
    if not service:
        return []

    query = f"'{folder_id}' in parents and trashed=false"

    results = (
        service.files()
        .list(q=query, fields="files(id, name, mimeType, modifiedTime)")
        .execute()
    )

    return results.get("files", [])


# ----------------------------------------------------------------------
# 4. File Content Extraction (TXT + DOCX + GOOGLE DOCS + PDF + fallback)
# ----------------------------------------------------------------------
def api_get_file_content(service, file_id, mime_type):
    """
    Downloads the content of a file.
    Handles:
    - Google Docs → export to text
    - DOCX → python-docx extraction
    - PDF → pdfplumber extraction
    - TXT or any unknown text → decode bytes
    """
    if not service:
        return ""

    # -------------------------------------------------------------
    # (A) GOOGLE DOCS EXPORT
    # -------------------------------------------------------------
    if mime_type.startswith("application/vnd.google-apps"):
        try:
            request = service.files().export(
                fileId=file_id, mimeType="text/plain"
            )
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

            return fh.getvalue().decode("utf-8", errors="ignore")

        except Exception as e:
            print(f"Error exporting Google Doc {file_id}: {e}")
            return ""


    # -------------------------------------------------------------
    # (B) DOCX EXTRACTION
    # -------------------------------------------------------------
    if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        try:
            request = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            from docx import Document
            doc = Document(io.BytesIO(fh.getvalue()))
            full_text = "\n".join([p.text for p in doc.paragraphs])
            return full_text

        except Exception as e:
            print(f"Error extracting DOCX {file_id}: {e}")
            return ""


    # -------------------------------------------------------------
    # (C) PDF EXTRACTION USING pdfplumber  ✅ NEW
    # -------------------------------------------------------------
    if mime_type == "application/pdf":
        try:
            request = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            import pdfplumber

            text = ""
            with pdfplumber.open(io.BytesIO(fh.getvalue())) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"

            return text.strip()

        except Exception as e:
            print(f"Error extracting PDF {file_id}: {e}")
            return ""


    # -------------------------------------------------------------
    # (D) DEFAULT BINARY/TEXT FALLBACK
    # -------------------------------------------------------------
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        return fh.getvalue().decode("utf-8", errors="ignore")

    except Exception as e:
        print(f"Error retrieving file {file_id}: {e}")
        return ""


# ----------------------------------------------------------------------
# 5. Combine All Files (Patient, Guidelines, Frameworks)
# ----------------------------------------------------------------------
def list_data_files():
    service = get_drive_service()
    if not service:
        return []

    patient_data_files = api_get_files_in_folder(service, FOLDER_ID_PATIENT_DATA)
    guideline_files = api_get_files_in_folder(service, FOLDER_ID_GUIDELINES)
    framework_files = api_get_files_in_folder(service, FOLDER_ID_PROMPT_FRAMEWORK)

    for f in patient_data_files:
        f["source"] = "patient_data"
    for f in guideline_files:
        f["source"] = "guidelines"
    for f in framework_files:
        f["source"] = "prompt_framework"

    all_files = patient_data_files + guideline_files + framework_files
    return sorted(all_files, key=lambda x: x["modifiedTime"], reverse=True)


# ----------------------------------------------------------------------
# 6. Framework Loader
# ----------------------------------------------------------------------
def get_framework_content():
    service = get_drive_service()
    if not service:
        return ""

    framework_files = api_get_files_in_folder(service, FOLDER_ID_PROMPT_FRAMEWORK)

    full_framework_content = []

    for file in framework_files:
        print(f"Retrieving framework content: {file['name']}")
        content = api_get_file_content(service, file["id"], file["mimeType"])

        section = (
            f"--- START OF PROMPT FRAMEWORK: {file['name']} ---\n"
            f"{content}\n"
            f"--- END OF PROMPT FRAMEWORK: {file['name']} ---"
        )

        full_framework_content.append(section)

    return "\n\n".join(full_framework_content)


# ----------------------------------------------------------------------
# 7. Upload File
# ----------------------------------------------------------------------
def upload_file(uploaded_file):
    service = get_drive_service()
    if not service:
        return "Upload failed: Service not initialized."

    target_folder_id = FOLDER_ID_PATIENT_DATA
    temp_path = uploaded_file.name

    try:
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        file_metadata = {"name": uploaded_file.name, "parents": [target_folder_id]}
        media = MediaFileUpload(temp_path, resumable=True)
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()

        os.remove(temp_path)
        return uploaded_file.name

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)

        print(f"Upload failed: {e}")
        return f"Upload failed: {e}"


# ----------------------------------------------------------------------
# 8. Delete File
# ----------------------------------------------------------------------
def delete_file(file_id):
    service = get_drive_service()
    if not service:
        return

    try:
        service.files().delete(fileId=file_id).execute()
        print(f"File ID {file_id} deleted.")
    except Exception as e:
        print(f"Error deleting file {file_id}: {e}")
