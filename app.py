from flask import Flask, render_template
import threading
import telebot
import os
from dotenv import load_dotenv

# .env fayldan tokenni o‘qish
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")  # .env ichida BOT_TOKEN=... bo‘lishi kerak

# Flask ilovasi
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/404')
def error_404():
    return render_template('404.html')

@app.route('/admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/buyruqlar')
def buyruqlar():
    return render_template('buyruqlar.html')

@app.route('/faoliyat')
def faoliyat():
    return render_template('faoliyat.html')

@app.route('/lavozimlar')
def lavozimlar():
    return render_template('lavozimlar.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/mfylar')
def mfylar():
    return render_template('mfylar.html')

@app.route('/sozlamalar')
def sozlamalar():
    return render_template('sozlamalar.html')

@app.route('/tumanlar')
def tumanlar():
    return render_template('tumanlar.html')

@app.route('/viloyatlar')
def viloyatlar():
    return render_template('viloyatlar.html')

@app.route('/xodim-qoshish')
def xodim_qoshish():
    return render_template('xodim_qoshish.html')

@app.route('/xodimlar')
def xodimlar():
    return render_template('xodimlar.html')

@app.route('/zahirakod')
def zahirakod():
    return render_template('zahirakod.html')

# 🔹 404 sahifa uchun maxsus handler
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


# === TELEGRAM BOT QISMI ===
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.reply_to(message, "Salom jigar! 😎 Flask bilan birga ishlaydigan bot ishlayapti!")

def run_bot():
    print("🤖 Bot ishga tushdi...")
    bot.infinity_polling()


# === FLASK + BOT BIRGALIKDA ISHLAYDI ===
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()  # Botni alohida oqimda ishga tushirish
    print("🌐 Flask server ishga tushdi...")
    app.run(host="0.0.0.0", port=8000, debug=True)