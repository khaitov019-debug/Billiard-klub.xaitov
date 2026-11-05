BILYARD CLUB — RAILWAY WEB VERSIYA

MUHIM: ZIP ichidagi fayllarni GitHub repository'ning ENG ASOSIY (root) qismiga yuklang.
app.py bilan templates va static papkalari bir darajada turishi SHART.

To'g'ri tuzilma:
app.py
requirements.txt
Procfile
runtime.txt
README_UZ.txt
templates/index.html
templates/reports.html
templates/settings.html
static/style.css

NOTO'G'RI: app.py rootda turib, templates papkasi boshqa ichki papkada qolishi.

GITHUBGA YUKLASH:
1. ZIP faylni kompyuterga yuklab oling va Extract All qiling.
2. Ochilgan BILYARD_CLUB_RAILWAY papkasiga kiring.
3. Ichidagi HAMMA fayl va papkalarni belgilang (app.py, templates, static va boshqalar).
4. GitHub repository sahifasida Add file > Upload files ni bosing.
5. Belgilangan fayl va papkalarni yuklang, pastda Commit changes ni bosing.
6. Railway avtomatik qayta deploy qiladi.

RAILWAY:
- Service > Settings > Networking > Generate Domain orqali link oling.
- Ma'lumotlar yo'qolmasligi uchun Railway Volume yarating va /data ga ulang.
- Variables ichida DATABASE_PATH=/data/club_data.db va SECRET_KEY uchun maxfiy qiymat kiriting.

Eslatma: bu web-versiyada stol band qilish, pauza/davom ettirish, tugatish, mahsulot qo'shish,
hisobot va narx sozlash mavjud. Eski Tkinter dasturidagi barcha qo'shimcha imkoniyatlar
hali to'liq ko'chirilmagan.
