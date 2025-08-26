# bot_main.py
import asyncio
import ocr_logic
import note_processor
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import io
import logging

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- Bot Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message explaining the bot's dual functionality."""
    await update.message.reply_text(
        "Hello! I'm your multi-function Expense Bot.\n\n"
        "➡️ Send me a photo of a receipt to process it.\n"
        "➡️ Send me a text note of your purchases to convert it into a receipt."
    )

async def handle_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming text messages, assuming they are shopping notes."""
    note_text = update.message.text
    if not note_text:
        return

    await update.message.reply_text("Note received! Converting to receipt format...")
    try:
        # 1. Convert the note to structured receipt data
        receipt_data = await note_processor.convert_note_to_receipt(note_text)
        
        # 2. Get AI-powered insights
        insights = await ocr_logic.get_receipt_insights(receipt_data)
        final_data = {**receipt_data, **insights}
        
        # 3. Log to Google Sheets
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, ocr_logic.log_to_google_sheet, final_data)
        
        # 4. Send the results back to the user
        await ocr_logic.send_telegram_message(final_data)
    except Exception as e:
        error_message = f"An error occurred while processing your note: {e}"
        print(error_message)
        await update.message.reply_text(
            "Sorry, I couldn't understand that note. Please try formatting it a bit more clearly."
        )

async def handle_receipt_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming photos, assuming they are receipts."""
    if not update.message.photo:
        return

    await update.message.reply_text("Receipt photo received! Processing...")
    try:
        # Download the photo
        photo_file = await update.message.photo[-1].get_file()
        image_stream = io.BytesIO()
        await photo_file.download_to_memory(image_stream)
        image_bytes = image_stream.getvalue()
        
        # 1. Extract structured data from the image
        extracted_data_json = await ocr_logic.process_receipt_image(image_bytes)
        extracted_data = json.loads(extracted_data_json)
        
        # 2. Get AI-powered insights
        insights = await ocr_logic.get_receipt_insights(extracted_data)
        final_data = {**extracted_data, **insights}
        
        # 3. Log the data to Google Sheets
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, ocr_logic.log_to_google_sheet, final_data)
        
        # 4. Send the final results back to the user
        await ocr_logic.send_telegram_message(final_data)
    except Exception as e:
        error_message = f"An error occurred while processing the photo: {e}"
        print(error_message)
        await update.message.reply_text(
            "Sorry, I couldn't process that receipt photo. Please try again."
        )

def main() -> None:
    """Starts the bot and adds handlers for both photos and text."""
    print("Starting multi-function bot...")
    application = Application.builder().token(ocr_logic.TELEGRAM_BOT_TOKEN).build()

    # Add command handler
    application.add_handler(CommandHandler("start", start))

    # ✨ Add handlers for BOTH photos and text messages ✨
    application.add_handler(MessageHandler(filters.PHOTO, handle_receipt_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_note))

    # Run the bot
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
