import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Google Sheets API için yetkilendirme
credentials_json = os.getenv("GOOGLE_CREDENTIALS")

if credentials_json:
    credentials_dict = json.loads(credentials_json)
    CREDENTIALS = ServiceAccountCredentials.from_json_keyfile_dict(
        credentials_dict, 
        ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
else:
    raise ValueError("Google Sheets kimlik bilgileri bulunamadı!")

# Google Sheets'e bağlan
gc = gspread.authorize(CREDENTIALS)

# Google Sheets URL'ini çevresel değişkenden al
SPREADSHEET_URL = os.getenv("GOOGLE_SHEETS_URL")

if not SPREADSHEET_URL:
    raise ValueError("Google Sheets URL'si bulunamadı!")

# Google Sheets dosyasını aç
spreadsheet = gc.open_by_url(SPREADSHEET_URL)

# Yeni bir çalışma sayfası ekle (tarih ve saat ile isimlendirilmiş)
sheet_name = datetime.now().strftime("Data_%Y%m%d_%H%M%S")
worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="10")

# Örnek veri ekle
worksheet.append_row(["Tarih", "Durum"])
worksheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Başarıyla eklendi!"])

print(f"Yeni çalışma sayfası eklendi: {sheet_name}")
