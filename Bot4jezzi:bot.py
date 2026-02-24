import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import openpyxl
import csv
import pdfplumber
import tempfile

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("No BOT_TOKEN set in environment")

user_data = {}

def excel_to_csv(excel_bytes, original_name):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
        tmp.write(excel_bytes)
        tmp_path = tmp.name
    wb = openpyxl.load_workbook(tmp_path)
    sheet = wb.active
    data = [list(row) for row in sheet.iter_rows(values_only=True)]
    csv_path = tmp_path.replace('.xlsx', '.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(data)
    os.unlink(tmp_path)
    return csv_path

def pdf_to_text(pdf_bytes, original_name):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    text = ""
    with pdfplumber.open(tmp_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    txt_path = tmp_path.replace('.pdf', '.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(text)
    os.unlink(tmp_path)
    return txt_path

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Freelance AI Bot\n\n"
        "Send me an Excel or PDF file, then use:\n"
        "/excel_to_csv\n/pdf_to_text"
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)
    file_bytes = await file.download_as_bytearray()
    user_data[user_id] = {
        'bytes': file_bytes,
        'name': doc.file_name,
        'mime': doc.mime_type
    }
    if 'excel' in doc.mime_type:
        await update.message.reply_text("Excel received. Use /excel_to_csv")
    elif doc.mime_type == 'application/pdf':
        await update.message.reply_text("PDF received. Use /pdf_to_text")
    else:
        await update.message.reply_text("File received. Use appropriate command.")

async def excel_to_csv_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        await update.message.reply_text("Send an Excel file first.")
        return
    data = user_data[user_id]
    if 'excel' not in data['mime']:
        await update.message.reply_text("That wasn't an Excel file.")
        return
    await update.message.reply_text("Converting...")
    try:
        out = excel_to_csv(data['bytes'], data['name'])
        with open(out, 'rb') as f:
            await update.message.reply_document(f, filename=out.split('/')[-1])
        os.unlink(out)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def pdf_to_text_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        await update.message.reply_text("Send a PDF file first.")
        return
    data = user_data[user_id]
    if data['mime'] != 'application/pdf':
        await update.message.reply_text("That wasn't a PDF.")
        return
    await update.message.reply_text("Extracting...")
    try:
        out = pdf_to_text(data['bytes'], data['name'])
        with open(out, 'rb') as f:
            await update.message.reply_document(f, filename=out.split('/')[-1])
        os.unlink(out)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("excel_to_csv", excel_to_csv_cmd))
    app.add_handler(CommandHandler("pdf_to_text", pdf_to_text_cmd))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
