from anthropic import Anthropic
import io
import os
import streamlit as st
from rapidfuzz import fuzz
import requests


from drive_manager import (
    list_data_files,
    get_drive_service,
    api_get_files_in_folder,
    api_get_file_content,
    FOLDER_ID_PROMPT_FRAMEWORK,
    get_guideline_filenames
)
client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

#For pulling data from postgres api
def fetch_patient_data():
    print("Calling patient data API...")

    url = "https://backend.qa.continuumcare.ai/api/llm/data?user_id=182&page=2&size=20"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {st.secrets['API_BEARER_TOKEN']}"
    }

    try:
        r = requests.get(url, headers=headers)
        print("Status:", r.status_code)
        print("Queried URL:", url)
        print("Raw text:", r.text[:200])

        return r.json()

    except Exception as e:
        print("Error:", e)
        return None


def fetch_patient_data_by_id(_):
    print("Fetching HARD-CODED patient URL...")

    url = "https://backend.qa.continuumcare.ai/api/llm/data?user_id=182&page=2&size=20"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {st.secrets['API_BEARER_TOKEN']}"
    }

    try:
        r = requests.get(url, headers=headers)
        print("Status:", r.status_code)
        print("Queried URL:", url)
        print("Raw text:", r.text[:200])

        return r.json()

    except Exception as e:
        print("Error:", e)
        return None


def load_frameworks():
    """Load all framework files, extract function names, and show detailed logs."""
    print("\n========================")
    print(" Loading framework files...")
    print("========================\n")

    service = get_drive_service()

    print(" Framework folder ID:", FOLDER_ID_PROMPT_FRAMEWORK)

    # Get files in the framework folder
    framework_files = api_get_files_in_folder(service, FOLDER_ID_PROMPT_FRAMEWORK)

    print("Files returned from Drive:", [f["name"] for f in framework_files])

    frameworks = []

    for f in framework_files:
        print("\n--------------------------------")
        print(" Reading file:", f["name"])
        print("--------------------------------")

        # Load full content
        content = api_get_file_content(service, f["id"], f["mimeType"])

        if not content:
            print("⚠️ File content EMPTY or unreadable.")
            continue

        # Extract first line
        first_line = content.split("\n")[0]
        print(" Raw first line:", repr(first_line))

        # Remove BOM + whitespace
        clean_first_line = first_line.lstrip("\ufeff").strip()
        print(" Cleaned first line:", repr(clean_first_line))

        # Check for Function header
        if clean_first_line.lower().startswith("function:"):
            function_name = clean_first_line.replace("Function:", "").strip()
            print("✅ Framework detected. Function name:", function_name)

            frameworks.append({
                "name": function_name,
                "content": content
            })
        else:
            print("This file does NOT start with 'Function:' — skipped.")

    print("\n Total frameworks loaded:", len(frameworks))
    print("========================\n")

    return frameworks



# ---------------------------------------------------------
# FUZZY MATCH CHOOSER
# ---------------------------------------------------------
def choose_best_framework(user_query, frameworks):
    """Pick the closest matching framework using fuzzy matching."""
    best_score = -1
    best_framework = frameworks[0]

    for fw in frameworks:
        score = fuzz.partial_ratio(user_query.lower(), fw["name"].lower())
        if score > best_score:
            best_score = score
            best_framework = fw

    print(f"🔍 Fuzzy Score: {best_score} for {best_framework['name']}")
    return best_framework


# ---------------------------------------------------------
# MAIN RESPONSE GENERATOR
# ---------------------------------------------------------
def generate_response(user_query):
    print("\n🔍 Starting generate_response()")
    service = get_drive_service()
    all_files = list_data_files()

    # 1. Load & match framework
    frameworks = load_frameworks()
    best_fw = choose_best_framework(user_query, frameworks)

    chosen_framework_name = best_fw["name"]
    framework_text = best_fw["content"]

    print(f"🧠 Chosen Framework: {chosen_framework_name}")

    system_prompt = f"""
You MUST strictly follow the framework below. 
Do not ignore, modify, or override any part of it.

=== FRAMEWORK START: {chosen_framework_name} ===
{framework_text}
=== FRAMEWORK END ===
"""

    # ----------------------------------------------------------
    # 2. LOAD PATIENT DATA FIRST (IMPORTANT!)
    # ----------------------------------------------------------
    patient_text = ""
    for f in all_files:
        if f.get("source") == "patient_data":
            content = api_get_file_content(service, f["id"], f["mimeType"])
            patient_text += f"\n\n---\nPATIENT FILE: {f['name']}\n{content}"

    # ----------------------------------------------------------
    # 3. GUIDELINE SELECTION (FILENAMES + PATIENT DATA)
    # ----------------------------------------------------------
    guideline_files = get_guideline_filenames()
    filename_list = [f["name"] for f in guideline_files]

    selector_prompt = f"""
You are the guideline selector for a health summarization system.

Below is the patient's complete clinical data (all patient files):

=== PATIENT DATA ===
{patient_text}

---

User query:
"{user_query}"

Below is the list of available ADA guideline documents:
{chr(10).join(['- ' + name for name in filename_list])}

Your task:
1. Identify the patient's main clinical issues from the combined data above.
2. Select ONLY the guideline files relevant to those issues.
3. Return ONLY a JSON array of filenames.

Example:
["ADA Glycemic Goals and Hypoglycemia 2025.pdf",
 "ADA ChronicKidneyDiseaseAndRiskMgmt Diabetes 2025.pdf"]
"""

    print("📁 Asking Claude to select relevant guideline filenames...")

    selector_resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": selector_prompt}]
    )

    raw_json = selector_resp.content[0].text
    print("🔍 Claude selector output:", raw_json)

    import json
    try:
        selected_filenames = json.loads(raw_json)
    except:
        selected_filenames = filename_list[:3]   # safe fallback

    print("📌 Selected guideline files:", selected_filenames)

    # ----------------------------------------------------------
    # 4. LOAD ONLY SELECTED GUIDELINE TEXT
    # ----------------------------------------------------------
    selected_guideline_text = ""

    for f in guideline_files:
        if f["name"] in selected_filenames:
            content = api_get_file_content(service, f["id"], f["mimeType"])
            selected_guideline_text += f"\n\n---\nGUIDELINE FILE: {f['name']}\n{content}"

    # ----------------------------------------------------------
    # 5. Final prompt
    # ----------------------------------------------------------
    user_message = f"""
Below are the materials you may use:

=== PATIENT DATA ===
{patient_text}

=== SELECTED ADA GUIDELINES ===
{selected_guideline_text}

---

User's question: {user_query}
"""

    print("🧠 Sending final request to Claude...")

    final_resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    return final_resp.content[0].text
