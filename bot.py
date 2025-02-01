import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.binary_location = "/usr/bin/google-chrome"
    service = Service('/usr/local/bin/chromedriver')
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_jobs(url, count):
    jobs = []
    try:
        # BeautifulSoup ile deneyelim önce
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Debug için HTML'i yazdır
        print("HTML Content:", soup.prettify()[:500])  # İlk 500 karakteri göster
        
        # İş ilanlarını bul
        job_listings = soup.find_all('div', class_='jv-list-item')
        print(f"Found {len(job_listings)} job listings")
        
        if not job_listings:
            print("BeautifulSoup failed, trying Selenium...")
            # Selenium ile dene
            driver = setup_driver()
            try:
                driver.get(url)
                time.sleep(5)  # Sayfanın yüklenmesi için bekle
                
                # Debug için sayfa kaynağını yazdır
                print("Selenium page source:", driver.page_source[:500])
                
                wait = WebDriverWait(driver, 10)
                job_elements = wait.until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "jv-list-item"))
                )
                
                for job_element in job_elements[:count]:
                    try:
                        vacancy = job_element.find_element(By.CLASS_NAME, "jv-list-item__title").text.strip()
                        job_link = job_element.find_element(By.TAG_NAME, "a").get_attribute("href")
                        
                        # Yeni sekmede aç
                        driver.execute_script(f"window.open('{job_link}');")
                        driver.switch_to.window(driver.window_handles[1])
                        time.sleep(3)
                        
                        description = driver.find_element(By.CLASS_NAME, "jv-job-detail__description").text.strip()
                        contact_info = driver.find_element(By.CLASS_NAME, "jv-job-detail__contact").text.strip()
                        
                        jobs.append({
                            'email': contact_info,
                            'vacancy': vacancy,
                            'description': description
                        })
                        
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        
                    except Exception as e:
                        print(f"Individual job error: {str(e)}")
                        continue
                        
            except Exception as e:
                print(f"Selenium error: {str(e)}")
            finally:
                driver.quit()
        else:
            # BeautifulSoup başarılı olduysa
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
    application.run_polling(poll_interval=3.0, timeout=30)

if __name__ == '__main__':
    main() 
