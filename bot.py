import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Environment variables'dan token'ı al
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SHEET_URL = os.getenv("GOOGLE_SHEET_URL")
FORM_URL = os.getenv("GOOGLE_FORM_URL")

# Form field ID'leri
FORM_FIELDS = {
    'email': os.getenv("FORM_EMAIL_FIELD", 'entry.2079815819'),
    'vacancy': os.getenv("FORM_VACANCY_FIELD", 'entry.99561878'),
    'description': os.getenv("FORM_DESCRIPTION_FIELD", 'entry.1802273569')
}

def scrape_jobs(url, count):
    jobs = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        job_listings = soup.find_all('div', class_='jv-list-item')
        print(f"Found {len(job_listings)} job listings")
        
        for job in job_listings[:count]:
            try:
                vacancy = job.find('h3', class_='jv-list-item__title').text.strip()
                description = job.find('div', class_='jv-list-item__description').text.strip()
                contact_info = job.find('div', class_='jv-list-item__contact').text.strip()
                
                jobs.append({
                    'email': contact_info,
                    'vacancy': vacancy,
                    'description': description
                })
            except Exception as e:
                print(f"BeautifulSoup job error: {str(e)}")
                continue
                
    except Exception as e:
        print(f"Main scraping error: {str(e)}")
    
    return jobs

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Merhaba! Web scraping botuna hoş geldiniz.\n"
        "Veri çekmek için /scrape komutunu kullanın."
    )

async def scrape(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Lütfen URL ve çekilecek ilan sayısını girin.\n"
        "Örnek format: https://site.com 10"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.split()
        if len(text) != 2:
            await update.message.reply_text("Hatalı format! Örnek: URL SAYI")
            return

        url = text[0]
        count = int(text[1])

        await update.message.reply_text("Veriler çekiliyor, lütfen bekleyin...")

        jobs = scrape_jobs(url, count)
        
        if not jobs:
            await update.message.reply_text("Veri çekilemedi veya hiç ilan bulunamadı.")
            return

        save_to_sheets(jobs)
        
        await update.message.reply_text(
            f"Veriler başarıyla kaydedildi!\n"
            f"Google Sheets'i kontrol edebilirsiniz: {SHEET_URL}"
        )

    except Exception as e:
        await update.message.reply_text(f"Bir hata oluştu: {str(e)}")

def save_to_sheets(jobs):
    try:
        for job in jobs:
            form_data = {
                FORM_FIELDS['email']: job['email'],
                FORM_FIELDS['vacancy']: job['vacancy'],
                FORM_FIELDS['description']: job['description']
            }
            
            response = requests.post(FORM_URL, data=form_data)
            if response.status_code != 200:
                print(f"Form submission error: {response.status_code}")
            time.sleep(1)
            
    except Exception as e:
        print(f"Sheets error: {str(e)}")

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("scrape", scrape))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot başlatılıyor...")
 

if __name__ == '__main__':
    main()
    

