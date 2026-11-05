BILYARD CLUB — RAILWAY WEB VERSIYA

GitHub repo ichiga ZIP ichidagi fayllarni ochib joylang:
- app.py
- requirements.txt
- Procfile
- railway.json
- templates papkasi (ichidagi HTML fayllari bilan)
- static papkasi

Railway avtomatik deploy qiladi. Railway Variables ichida SECRET_KEY uchun uzun maxfiy qiymat qo'yish tavsiya etiladi.

Muhim: Railway fayl tizimi doimiy saqlanishi uchun Railway Volume ulab, DB_PATH ni volume ichiga yo'naltirish kerak. Aks holda deploy qayta ishga tushganda SQLite ma'lumotlari yo'qolishi mumkin.

Bu dastlabki web ko'chirma. Asl Tkinter oynalari web sahifalarga almashtirilgan; stol band qilish/tugatish/pauza, mahsulot qo'shish, SQLite, hisobot va narx sozlamalari bor. Avval Railway'da sinab ko'ring.
