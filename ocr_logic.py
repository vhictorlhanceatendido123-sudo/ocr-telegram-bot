# ocr_logic.py
import google.generativeai as genai
import os
from PIL import Image
import io
import json
import telegram
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

# --- Configuration ---
# Define the path to the config file
config_path = "config.env"

# ✨ NEW: Check if the config.env file exists before trying to load it
if not os.path.exists(config_path):
    raise FileNotFoundError(
        "The 'config.env' file was not found. "
        "Please make sure it is in the same directory as your scripts and is named correctly."
    )

# Load environment variables from the 'config.env' file
load_dotenv(dotenv_path=config_path)

# IMPORTANT: Set these environment variables in your config.env file.
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
    TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
    GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
except KeyError as e:
    raise ValueError(f"{e.args[0]} environment variable not set in config.env")

# --- JSON Schema for Structured Output ---
receipt_schema = {
    "type": "OBJECT",
    "properties": {
        "vendor_name": {"type": "STRING", "description": "The name of the store or vendor."},
        "receipt_date": {"type": "STRING", "description": "The date on the receipt (e.g., YYYY-MM-DD)."},
        "total_amount": {"type": "STRING", "description": "The final total amount paid."},
        "line_items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "description": {"type": "STRING", "description": "Description of the purchased item."},
                    "amount": {"type": "STRING", "description": "Price of the individual item."}
                },
                "required": ["description", "amount"]
            }
        }
    },
    "required": ["vendor_name", "receipt_date", "total_amount"]
}

# --- Core OCR Function ---
async def process_receipt_image(image_bytes: bytes):
    """Processes a receipt image using the Gemini 1.5 Pro model to extract structured data."""
    print("Processing image with Gemini API for OCR...")
    try:
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=receipt_schema
        )
        model = genai.GenerativeModel(
            "gemini-1.5-pro-latest",
            generation_config=generation_config
        )
        img = Image.open(io.BytesIO(image_bytes))
        prompt = "Analyze this receipt image and extract the vendor name, date, line items, and the final total amount. Format the output according to the provided JSON schema."
        response = await model.generate_content_async([prompt, img])
        print("Successfully extracted data from receipt.")
        return response.text
    except Exception as e:
        print(f"Error during Gemini API OCR call: {e}")
        raise

# --- Gemini-Powered Insight Generation ---
async def get_receipt_insights(receipt_data: dict):
    """Uses a Gemini LLM to categorize the expense and generate an expense memo."""
    print("Generating insights with Gemini API...")
    try:
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        prompt = f"""
        Based on the following receipt data, please perform two tasks:
        1.  Categorize this expense into one of the following common business categories: Food & Dining, Travel, Office Supplies, Transportation, Utilities, or Other.
        2.  Write a concise, one-sentence expense memo describing the purchase.

        Receipt Data:
        {json.dumps(receipt_data, indent=2)}

        Provide the output as a JSON object with two keys: "category" and "memo".
        """
        response = await model.generate_content_async(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        insights = json.loads(cleaned_response)
        print("Successfully generated insights.")
        return insights
    except Exception as e:
        print(f"Error during Gemini API insight generation: {e}")
        return {"category": "Uncategorized", "memo": "Could not generate memo."}

# --- Telegram Bot Notification ---
async def send_telegram_message(receipt_data: dict):
    """Sends a formatted message to a Telegram chat."""
    print("Sending notification to Telegram...")
    try:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        message = (
            f"🧾 *New Receipt Processed!*\n\n"
            f"*Vendor:* {receipt_data.get('vendor_name', 'N/A')}\n"
            f"*Date:* {receipt_data.get('receipt_date', 'N/A')}\n"
            f"*Total:* {receipt_data.get('total_amount', 'N/A')}\n"
            f"*Category:* {receipt_data.get('category', 'N/A')}\n\n"
            f"*Memo:* _{receipt_data.get('memo', 'N/A')}_"
        )
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='Markdown')
        print("Telegram message sent successfully.")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        pass

# --- Google Sheets Logging ---
def log_to_google_sheet(receipt_data: dict):
    """Appends a new row with receipt data to a Google Sheet."""
    print("Logging data to Google Sheet...")
    try:
        creds = service_account.Credentials.from_service_account_file(
            'credentials.json',
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        row_data = [
            receipt_data.get('receipt_date', ''),
            receipt_data.get('vendor_name', ''),
            receipt_data.get('total_amount', ''),
            receipt_data.get('category', ''),
            receipt_data.get('memo', ''),
        ]
        sheet.values().append(
            spreadsheetId=GOOGLE_SHEET_ID,
            range='Sheet1!A1',
            valueInputOption='USER_ENTERED',
            body={'values': [row_data]}
        ).execute()
        print("Google Sheet updated successfully.")
    except Exception as e:
        print(f"Error logging to Google Sheet: {e}")
        pass
