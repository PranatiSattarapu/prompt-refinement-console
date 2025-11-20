from anthropic import Anthropic
import io
import os
import streamlit as st
from rapidfuzz import fuzz

from drive_manager import (
    list_data_files,
    get_drive_service,
    api_get_files_in_folder,
    api_get_file_content,
    FOLDER_ID_PROMPT_FRAMEWORK
)

client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])


# ---------------------------------------------------------
# LOAD ALL FRAMEWORKS
# ---------------------------------------------------------
def load_frameworks():
    """Load all framework files, extract function names, and show detailed logs."""
    print("\n========================")
    print("🔎 Loading framework files...")
    print("========================\n")

    service = get_drive_service()

    print("📁 Framework folder ID:", FOLDER_ID_PROMPT_FRAMEWORK)

    # Get files in the framework folder
    framework_files = api_get_files_in_folder(service, FOLDER_ID_PROMPT_FRAMEWORK)

    print("🗂 Files returned from Drive:", [f["name"] for f in framework_files])

    frameworks = []

    for f in framework_files:
        print("\n--------------------------------")
        print("📄 Reading file:", f["name"])
        print("--------------------------------")

        # Load full content
        content = api_get_file_content(service, f["id"], f["mimeType"])

        if not content:
            print("⚠️ File content EMPTY or unreadable.")
            continue

        # Extract first line
        first_line = content.split("\n")[0]
        print("🔍 Raw first line:", repr(first_line))

        # Remove BOM + whitespace
        clean_first_line = first_line.lstrip("\ufeff").strip()
        print("✨ Cleaned first line:", repr(clean_first_line))

        # Check for Function header
        if clean_first_line.lower().startswith("function:"):
            function_name = clean_first_line.replace("Function:", "").strip()
            print("✅ Framework detected. Function name:", function_name)

            frameworks.append({
                "name": function_name,
                "content": content
            })
        else:
            print("❌ This file does NOT start with 'Function:' — skipped.")

    print("\n📊 Total frameworks loaded:", len(frameworks))
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
    files = list_data_files()

    print(f"📂 Total files found: {len(files)}")

    # 1. Load and route frameworks
    frameworks = load_frameworks()
    best_fw = choose_best_framework(user_query, frameworks)

    chosen_framework_name = best_fw["name"]
    framework_text = best_fw["content"]

    print(f"🧠 Chosen Framework: {chosen_framework_name}")

    # 2. System prompt with chosen framework
    system_prompt = f"""
You MUST strictly follow the framework provided below.
Do NOT ignore, modify, or override any part of it.

=== FRAMEWORK START: {chosen_framework_name} ===
{framework_text}
=== FRAMEWORK END ===
"""

    # 3. Load patient data + guidelines
    combined_text = ""
    for f in files:
        if f.get('source') in ['patient_data', 'guidelines']:
            content = api_get_file_content(service, f["id"], f["mimeType"])
            combined_text += f"\n\n---\nDocument: {f['name']}\n{content}"

    # 4. Build user prompt
    user_message = f"""Here is the user's health data and relevant guidelines:

{combined_text}

---

User's question: {user_query}
"""

    print("🧠 Sending to Claude...")

    # 5. Send to Claude
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text
