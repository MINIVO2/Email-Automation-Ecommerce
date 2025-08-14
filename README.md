
# Email Automation using Gemini API

This Python script automatically:

- Reads unread Gmail messages.
- Generates professional replies using Google Gemini AI.
- Sends replies automatically.
- Logs email details and replies in a Google Sheet.
- Marks emails as read after processing.

It runs continuously on your desktop.

---

## Features

- Auto-fetch unread emails.
- Professional AI-generated replies.
- Logs email details to Google Sheets.
- Skips emails sent by your own account automatically.
- Fully desktop-based; no frontend required.

---

## Prerequisites

1. Python 3.10+ installed on your system.
2. Google Cloud Project with:
   - Gmail API enabled.
   - Google Sheets API enabled.
   - OAuth 2.0 credentials downloaded as `credentials.json`.
3. Add your Gmail account as a **Test User** if your project is in Testing mode.
4. Gemini AI API key from Google.

---

## Installation

1. Clone or download this repository:

```bash
git clone https://github.com/yourusername/gmail-auto-reply.git
cd gmail-auto-reply
````

2. Create a virtual environment and activate it:

```bash
python -m venv venv
# macOS/Linux
source venv/bin/activate
# Windows
venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

**Dependencies include:**

* `google-api-python-client`
* `google-auth-httplib2`
* `google-auth-oauthlib`
* `beautifulsoup4`
* `google-generativeai`

---

## Configuration

1. Set environment variable for Gemini AI API key:

```bash
# macOS/Linux
export GEMINI_API_KEY="your_gemini_api_key"

# Windows PowerShell
setx GEMINI_API_KEY "your_gemini_api_key"
```

2. Update script constants:

```python
SPREADSHEET_ID = "YOUR_GOOGLE_SHEET_ID"
SHEET_NAME = "Sheet1"
ARCHIVE_FOLDER = "email_archive"
```

3. Make sure `credentials.json` is in the same folder as the script.
4. Redirect URI in Google Cloud OAuth should be:

```
http://localhost:8080/
```

5. Add your Gmail as a **Test User** in OAuth consent screen if your app is in Testing mode.

---

## Running the Script

Run the script from your desktop:

```bash
python main.py
```

* The first time, a browser window opens for Google authentication.
* After authentication, the script runs continuously:

  1. Fetches unread emails.
  2. Generates AI replies.
  3. Sends replies.
  4. Logs details in Google Sheets.
  5. Marks emails as read.
* Sleeps for 20 minutes between each run (configurable via `time.sleep`).

---

## Notes

* Emails sent by your own account are skipped automatically.
* Only test users can authenticate if the project is in Testing mode.
* To use with other Gmail accounts, app verification by Google is required.

---

## Troubleshooting

* **redirect\_uri\_mismatch**:

  * Ensure redirect URI in Google Cloud matches exactly: `http://localhost:8080/`
  * Use the same `credentials.json` used to create OAuth credentials.
* **Cannot sign in**:

  * Add Gmail account as a Test User.
* **Gemini API errors**:

  * Verify that the `GEMINI_API_KEY` environment variable is correctly set.

---

## License

MIT License


