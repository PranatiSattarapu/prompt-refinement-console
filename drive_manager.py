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

def list_data_files_cached():
    """Cache drive results for 60 seconds"""
    return list_data_files()

# ----------------------------------------------------------------------
# 2. Authentication and Service Initialization
# ----------------------------------------------------------------------
def get_drive_service():
    """Loads Google service account from Streamlit Secrets."""
    try:
        service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
        creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )
        service = build("drive", "v3", credentials=creds)
        return service
    except Exception as e:
        print(f"Error initializing Google Drive service: {e}")
        return None
# ----------------------------------------------------------------------
# 3. Core Utility Functions
# ----------------------------------------------------------------------

def api_get_files_in_folder(service, folder_id):
    """Retrieves metadata for non-trashed files within a specific folder ID."""
    if not service:
        return []
        
    query = f"'{folder_id}' in parents and trashed=false"
    
    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType, modifiedTime)"
    ).execute()
    
    return results.get("files", [])


def api_get_file_content(service, file_id, mime_type):
    """
    Downloads the content of a file. Exports Google Workspace files to plain text.
    Returns content as a string.
    """
    if not service:
        return ""
    
    request = None
    
    # Check if the file is a Google Workspace Document (Docs, Sheets, Slides, etc.)
    if mime_type.startswith('application/vnd.google-apps'):
        # Export Google Docs to plain text
        target_mime = 'text/plain'
        request = service.files().export(fileId=file_id, mimeType=target_mime)
    else:
        # Download binary file content (like .txt, .pdf, or other regular files)
        request = service.files().get_media(fileId=file_id)

    # Use MediaIoBaseDownload to handle streaming of the response
    try:
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            # print(f"Download progress: {int(status.progress() * 100)}%") # Uncomment for debug
        
        # Decode the content (assuming text-based content is expected)
        return fh.getvalue().decode('utf-8', errors='ignore')
        
    except Exception as e:
        print(f"Error downloading content for file ID {file_id}: {e}")
        return f"Error retrieving content for file ID {file_id}."

# ----------------------------------------------------------------------
# 4. Application Logic Functions
# ----------------------------------------------------------------------

def list_data_files():
    service = get_drive_service()
    if not service:
        return []

    # Fetch all three folder types
    patient_data_files = api_get_files_in_folder(service, FOLDER_ID_PATIENT_DATA)
    guideline_files = api_get_files_in_folder(service, FOLDER_ID_GUIDELINES)
    framework_files = api_get_files_in_folder(service, FOLDER_ID_PROMPT_FRAMEWORK)

    for f in patient_data_files:
        f['source'] = 'patient_data'
    for f in guideline_files:
        f['source'] = 'guidelines'
    for f in framework_files:
        f['source'] = 'prompt_framework'

    # Combine all into one list
    all_files = patient_data_files + guideline_files + framework_files
    return sorted(all_files, key=lambda x: x['modifiedTime'], reverse=True)


def get_framework_content():
    """
    Retrieves and concatenates the content of all documents in the PROMPT_FRAMEWORK folder.
    This content acts as the constant, high-priority instruction set for the LLM.
    """
    service = get_drive_service()
    if not service:
        return ""
        
    framework_files = api_get_files_in_folder(service, FOLDER_ID_PROMPT_FRAMEWORK)
    
    full_framework_content = []
    
    for file in framework_files:
        print(f"Retrieving framework content: {file['name']}")
        content = api_get_file_content(service, file['id'], file['mimeType'])
        
        # Store content with a clear separator
        section = (
            f"--- START OF PROMPT FRAMEWORK: {file['name']} ---\n"
            f"{content}\n"
            f"--- END OF PROMPT FRAMEWORK: {file['name']} ---"
        )
        full_framework_content.append(section)
        
    return "\n\n".join(full_framework_content)


def upload_file(uploaded_file):
    """
    Upload a new file to the Patient Data folder by default.
    """
    service = get_drive_service()
    if not service:
        return "Upload failed: Service not initialized."
        
    target_folder_id = FOLDER_ID_PATIENT_DATA # Default upload target
    temp_path = uploaded_file.name

    # Save temporarily
    try:
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        file_metadata = {"name": uploaded_file.name, "parents": [target_folder_id]}
        media = MediaFileUpload(temp_path, resumable=True)
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()

        # Cleanup
        os.remove(temp_path)
        return uploaded_file.name
    except Exception as e:
        # Ensure temporary file is cleaned up even if Drive API fails
        if os.path.exists(temp_path):
             os.remove(temp_path)
        print(f"Upload failed: {e}")
        return f"Upload failed: {e}"


def delete_file(file_id):
    """Delete a file by its ID (hard delete from Drive)."""
    service = get_drive_service()
    if not service:
        return

    try:
        service.files().delete(fileId=file_id).execute()
        print(f"File ID {file_id} deleted successfully.")
    except Exception as e:
        print(f"Error deleting file ID {file_id}: {e}")

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
import os
import io
import json
import streamlit as st
# st.write("🔑 GOOGLE KEY IN SECRETS:", "GOOGLE_SERVICE_ACCOUNT" in st.secrets)

# try:
#     data = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
#     st.write("🟢 JSON LOAD SUCCESS")
# except Exception as e:
#     st.write("🔴 JSON LOAD ERROR:", str(e))

# service = get_drive_service()
# st.write("📁 DRIVE SERVICE:", service)
# ----------------------------------------------------------------------
# 1. Configuration (IDs and Scopes)
# ----------------------------------------------------------------------
FOLDER_ID_PATIENT_DATA = "17CdWnoybK0R7pKsdug7Oxo-Xd4iUVRCX"
FOLDER_ID_GUIDELINES = "1Wj-O-q9MCdYQz4Uo4zkNFtgPexbTj5rn"
FOLDER_ID_PROMPT_FRAMEWORK = "1A8oN2RYZMdOCZRmsC6d1kdyeAjzdzfw1"
SCOPES = ["https://www.googleapis.com/auth/drive"]

def list_data_files_cached():
    """Cache drive results for 60 seconds"""
    return list_data_files()

# ----------------------------------------------------------------------
# 2. Authentication and Service Initialization
# ----------------------------------------------------------------------
def get_drive_service():
    """Loads Google service account from Streamlit Secrets."""
    try:
        service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
        creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )
        service = build("drive", "v3", credentials=creds)
        return service
    except Exception as e:
        print(f"Error initializing Google Drive service: {e}")
        return None
# ----------------------------------------------------------------------
# 3. Core Utility Functions
# ----------------------------------------------------------------------

def api_get_files_in_folder(service, folder_id):
    """Retrieves metadata for non-trashed files within a specific folder ID."""
    if not service:
        return []
        
    query = f"'{folder_id}' in parents and trashed=false"
    
    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType, modifiedTime)"
    ).execute()
    
    return results.get("files", [])


def api_get_file_content(service, file_id, mime_type):
    """
    Downloads the content of a file.
    Handles:
    - Google Docs → export as text
    - .txt / .pdf / others → download raw
    - .docx → extract text properly using python-docx
    """
    if not service:
        return ""

    # --- 1. Handle Google Docs format ---
    if mime_type.startswith("application/vnd.google-apps"):
        request = service.files().export(fileId=file_id, mimeType="text/plain")
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        return fh.getvalue().decode("utf-8", errors="ignore")

    # --- 2. Handle DOCX files properly ---
    if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        # Download DOCX as bytes first
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        # Extract TEXT using python-docx
        from docx import Document
        doc = Document(io.BytesIO(fh.getvalue()))
        full_text = "\n".join([para.text for para in doc.paragraphs])
        return full_text

    # --- 3. Handle normal binary/text files (.txt, etc.) ---
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        return fh.getvalue().decode("utf-8", errors="ignore")

    except Exception as e:
        print(f"Error retrieving file content for file ID {file_id}: {e}")
        return f"Error retrieving content for file {file_id}."


# ----------------------------------------------------------------------
# 4. Application Logic Functions
# ----------------------------------------------------------------------

def list_data_files():
    service = get_drive_service()
    if not service:
        return []

    # Fetch all three folder types
    patient_data_files = api_get_files_in_folder(service, FOLDER_ID_PATIENT_DATA)
    guideline_files = api_get_files_in_folder(service, FOLDER_ID_GUIDELINES)
    framework_files = api_get_files_in_folder(service, FOLDER_ID_PROMPT_FRAMEWORK)

    for f in patient_data_files:
        f['source'] = 'patient_data'
    for f in guideline_files:
        f['source'] = 'guidelines'
    for f in framework_files:
        f['source'] = 'prompt_framework'

    # Combine all into one list
    all_files = patient_data_files + guideline_files + framework_files
    return sorted(all_files, key=lambda x: x['modifiedTime'], reverse=True)


def get_framework_content():
    """
    Retrieves and concatenates the content of all documents in the PROMPT_FRAMEWORK folder.
    This content acts as the constant, high-priority instruction set for the LLM.
    """
    service = get_drive_service()
    if not service:
        return ""
        
    framework_files = api_get_files_in_folder(service, FOLDER_ID_PROMPT_FRAMEWORK)
    
    full_framework_content = []
    
    for file in framework_files:
        print(f"Retrieving framework content: {file['name']}")
        content = api_get_file_content(service, file['id'], file['mimeType'])
        
        # Store content with a clear separator
        section = (
            f"--- START OF PROMPT FRAMEWORK: {file['name']} ---\n"
            f"{content}\n"
            f"--- END OF PROMPT FRAMEWORK: {file['name']} ---"
        )
        full_framework_content.append(section)
        
    return "\n\n".join(full_framework_content)


def upload_file(uploaded_file):
    """
    Upload a new file to the Patient Data folder by default.
    """
    service = get_drive_service()
    if not service:
        return "Upload failed: Service not initialized."
        
    target_folder_id = FOLDER_ID_PATIENT_DATA # Default upload target
    temp_path = uploaded_file.name

    # Save temporarily
    try:
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        file_metadata = {"name": uploaded_file.name, "parents": [target_folder_id]}
        media = MediaFileUpload(temp_path, resumable=True)
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()

        # Cleanup
        os.remove(temp_path)
        return uploaded_file.name
    except Exception as e:
        # Ensure temporary file is cleaned up even if Drive API fails
        if os.path.exists(temp_path):
             os.remove(temp_path)
        print(f"Upload failed: {e}")
        return f"Upload failed: {e}"


def delete_file(file_id):
    """Delete a file by its ID (hard delete from Drive)."""
    service = get_drive_service()
    if not service:
        return

    try:
        service.files().delete(fileId=file_id).execute()
        print(f"File ID {file_id} deleted successfully.")
    except Exception as e:
        print(f"Error deleting file ID {file_id}: {e}")