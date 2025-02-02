import logging
import requests
import gspread
import json
import time
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os

# Telegram Bot Token
TOKEN = os.getenv("7681213704:AAEZ8HLwU_Wrh3gaDo5ppDs2lt9hh86ibzI")

# Google Sheets Bağlantısı
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDENTIALS_PATH = "credentials.json"  # JSON dosyanızı yerel olarak saklayın
CREDENTIALS = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, SCOPE)
GC = gspread.authorize(CREDENTIALS)
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1wBNDIZBneb0Vd7v7K2HpUYz3QGHhxZETgyX4IoNcFdw/edit?gid=0#gid=0"  # Google Sheets linkiniz

# Loglama
logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Merhaba! Web scraping botuna hoş geldin. /scrape komutunu kullanarak veri çekebilirsin.")

async def scrape(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Lütfen şu formatta yaz: <link> <adet>")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text.split()
    if len(message) != 2:
        await update.message.reply_text("Yanlış format! Doğru format: <link> <adet>")
        return
    
    url, count = message
    count = int(count)
    await update.message.reply_text(f"{count} ilan çekiliyor... Lütfen bekleyin.")
    
    data = scrape_data(url, count)
    sheet_name = f"Scrape_{int(time.time())}"
    save_to_sheets(data, sheet_name)
    
    await update.message.reply_text(f"Veriler Google Sheets'e kaydedildi! Sheet adı: {sheet_name}")

def scrape_data(url, count):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    jobs = []
    
    job_cards = soup.find_all("div", class_="card")[:count]
    for job in job_cards:
        title = job.find("h2").text.strip()
        description = job.find("p").text.strip()
        email = job.find("a", href=True)["href"].replace("mailto:", "")
        jobs.append([title, description, email])
    
    return jobs

def save_to_sheets(data, sheet_name):
    spreadsheet = GC.open_by_url(SPREADSHEET_URL)
    sheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="3")
    sheet.append_row(["Job Title", "Description", "Email"])
    for row in data:
        sheet.append_row(row)

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scrape", scrape))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling()
