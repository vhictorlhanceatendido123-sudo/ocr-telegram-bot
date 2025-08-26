# note_processor.py
import google.generativeai as genai
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# --- Configuration ---
# Load environment variables from a specific file named 'config.env'
load_dotenv(dotenv_path="config.env")

try:
    # This will now read the keys loaded from your config.env file
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
except KeyError:
    raise ValueError("GOOGLE_API_KEY environment variable not set. Make sure it's in your config.env file.")

# --- JSON Schema for the AI's Output ---
# This tells Gemini exactly how we want the data structured.
note_to_receipt_schema = {
    "type": "OBJECT",
    "properties": {
        "vendor_name": {
            "type": "STRING",
            "description": "The name of the supermarket or store. Infer this from the note if possible, otherwise use 'General Store'."
        },
        "receipt_date": {
            "type": "STRING",
            "description": "The date of the purchase. If not mentioned, use today's date in YYYY-MM-DD format."
        },
        "total_amount": {
            "type": "STRING",
            "description": "The final total amount paid. Calculate this by summing all line items if not explicitly mentioned."
        },
        "line_items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "description": {"type": "STRING", "description": "Description of the purchased item."},
                    "quantity": {"type": "INTEGER", "description": "The quantity of the item purchased, default to 1 if not specified."},
                    "amount": {"type": "STRING", "description": "Price of the individual item or total for the quantity."}
                },
                "required": ["description", "amount", "quantity"]
            }
        }
    },
    "required": ["vendor_name", "receipt_date", "total_amount", "line_items"]
}

# --- Main Conversion Function ---
async def convert_note_to_receipt(note_text: str):
    """
    Uses the Gemini API to convert a raw text note into structured receipt data.

    Args:
        note_text: The user's unstructured shopping note.

    Returns:
        A dictionary containing the structured receipt data.
    """
    print("Converting note to receipt format with Gemini API...")
    try:
        # Configure the model to return JSON based on our schema
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=note_to_receipt_schema
        )
        model = genai.GenerativeModel(
            "gemini-1.5-pro-latest",
            generation_config=generation_config
        )
        
        # Get today's date to provide context to the model
        today_date = datetime.now().strftime("%Y-%m-%d")

        # A detailed prompt to guide the LLM
        prompt = f"""
        You are an expert data entry assistant. Analyze the following unstructured shopping note and convert it into a structured receipt format based on the provided JSON schema.

        - Today's date is {today_date}. Use this if no other date is mentioned.
        - The user is in the Philippines, so prices are in PHP.
        - Infer the vendor if possible (e.g., 'SM' means 'SM Supermarket').
        - Calculate the total by summing the item amounts if it's not stated.
        - Assume a quantity of 1 for items unless specified otherwise.

        Here is the note:
        ---
        {note_text}
        ---
        """

        response = await model.generate_content_async(prompt)
        print("Successfully converted note to structured data.")
        
        # The response text will be a JSON string, so we parse it
        return json.loads(response.text)

    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        raise
