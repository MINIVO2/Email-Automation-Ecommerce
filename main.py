import os
import base64
import re
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from datetime import datetime
from email.mime.text import MIMEText
import google.generativeai as genai
import time
# ---------------- CONFIGURATION ----------------
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/spreadsheets"
]
SPREADSHEET_ID = "Enter Your spreadsheet"
SHEET_NAME = "Sheet1"
ARCHIVE_FOLDER = "email_archive"

# Configure Gemini API Key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Ensure archive folder exists
if not os.path.exists(ARCHIVE_FOLDER):
    os.makedirs(ARCHIVE_FOLDER)

# ---------------- AUTHENTICATION ----------------
def authenticate_google():
    """Authenticate once for both Gmail and Sheets API and get the logged-in email."""
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    gmail_service = build("gmail", "v1", credentials=creds)
    sheets_service = build("sheets", "v4", credentials=creds)

    # ✅ Fetch authenticated account email
    profile = gmail_service.users().getProfile(userId="me").execute()
    my_email = profile.get("emailAddress", "").lower()

    return gmail_service, sheets_service, my_email


# ---------------- UTILITIES ----------------
def clean_email_body(html_content):
    """Remove HTML tags and extra spaces from email body."""
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text(separator="\n")
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def save_email_to_file(sender, subject, body_text):
    """Save full email content to a local file."""
    safe_subject = re.sub(r'[\\/*?:"<>|]', "_", subject)
    filename = f"{ARCHIVE_FOLDER}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_subject}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"From: {sender}\n")
        f.write(f"Subject: {subject}\n\n")
        f.write(body_text)
    return filename

def log_to_sheet(service, row_data):
    """Append a row to the Google Sheet."""
    try:
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A:H",  # 8 columns
            valueInputOption="RAW",
            body={"values": [row_data]}
        ).execute()
    except HttpError as error:
        print(f"❌ Failed to log to sheet: {error}")

# ---------------- GEMINI FUNCTIONS ----------------
def categorize_email(email_text):
    """Use Gemini to categorize the email."""
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"Classify the following email into a category like 'Support', 'Sales', 'Personal', 'Job Application', 'Spam', etc. Only output the category name.\n\n{email_text}"
    response = model.generate_content(prompt)
    return response.text.strip() if response.text else "Uncategorized"

def generate_reply(email_text, category=None):
    """Generate a professional, context-aware reply using Gemini AI."""
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"""
    You are an AI email assistant for a professional organization. Your task is to draft a concise, clear, and courteous reply to the email below. 
    The reply should:
    - Start with Dear Customer.
    - Maintain a professional and respectful tone.
    - Directly address the sender's concerns or requests.
    - Provide clear next steps or acknowledgement if no immediate action is required.
    - Use proper grammar, punctuation, and paragraph structure.
    - Avoid overly casual language.
    - Keep the length between 3 to 6 sentences.

    Email Category: {category}
    Email Content:
    {email_text}

    Reply:
    """
    response = model.generate_content(prompt)
    return response.text.strip() if response.text else "Thank you for your email. We will get back to you shortly."

# ---------------- GMAIL FUNCTIONS ----------------
def send_reply(service, thread_id, sender_email, original_subject, reply_body):
    """Send a Gmail reply."""
    reply_subject = "Re: " + original_subject
    message = MIMEText(reply_body)
    message['to'] = sender_email
    message['subject'] = reply_subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent_message = service.users().messages().send(
        userId="me",
        body={"raw": raw_message, "threadId": thread_id}
    ).execute()
    return sent_message


# ---------------- MAIN ----------------
def main():
    gmail_service, sheets_service, my_email = authenticate_google()

    # Fetch unread emails
    results = gmail_service.users().messages().list(
        userId="me", labelIds=["UNREAD"], maxResults=5
    ).execute()
    messages = results.get("messages", [])

    if not messages:
        print("📭 No new unread emails.")
        return

    for msg in messages:
        msg_data = gmail_service.users().messages().get(
            userId="me", id=msg["id"]
        ).execute()

        headers = msg_data["payload"]["headers"]
        sender = next((h["value"] for h in headers if h["name"] == "From"), "").lower()
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")

        # 🚫 Skip emails sent by yourself dynamically
        if my_email in sender:
            print(f"⏭ Skipping email from self: {sender}")
            gmail_service.users().messages().modify(
                userId="me",
                id=msg["id"],
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            continue

        # Extract body
        body_data = ""
        if "parts" in msg_data["payload"]:
            for part in msg_data["payload"]["parts"]:
                if part["mimeType"] == "text/html" and "data" in part["body"]:
                    body_data = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    break
                elif part["mimeType"] == "text/plain" and "data" in part["body"]:
                    body_data = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
        else:
            body_data = base64.urlsafe_b64decode(msg_data["payload"]["body"]["data"]).decode("utf-8")

        body_clean = clean_email_body(body_data)
        save_email_to_file(sender, subject, body_clean)

        # Categorize email
        category = categorize_email(body_clean)

        # Generate Gemini reply
        reply_text = generate_reply(body_clean, category)

        # Send actual reply
        send_reply(gmail_service, msg_data["threadId"], sender, subject, reply_text)

        # Prepare summary
        preview = (body_clean[:500] + "...") if len(body_clean) > 500 else body_clean

        # Log to Google Sheet
        log_to_sheet(
            sheets_service,
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Timestamp
                sender,              # From
                subject,             # Subject
                preview,             # Summary
                category,            # Category
                reply_text,          # Reply Sent
                "Auto-Reply Sent",   # Status
                msg["threadId"]      # Gmail Thread ID
            ]
        )

        # Mark email as read
        gmail_service.users().messages().modify(
            userId="me",
            id=msg["id"],
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()

        print(f"✅ Replied to {sender} ({category}) and logged in sheet.")



if __name__ == "__main__":
    while True:
        print(f"\n⏳ Running email check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        main()
        print("💤 Sleeping for 20 min...")
        time.sleep(20*60)  
