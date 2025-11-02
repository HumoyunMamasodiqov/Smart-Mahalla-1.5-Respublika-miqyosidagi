# bot_with_admin.py
import logging
import json
import os
import sys
import subprocess
import time
import signal
import atexit
import asyncio
import threading
import secrets
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import csv
import io

# Logger sozlamalari
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO  
logger = logging.getLogger(__name__)

# Ma'lumotlar bazasi fayllari
DATA_FILE = "data.json"
ADMINS_FILE = "admins.json"
SETTINGS_FILE = "settings.json"
ACTIVITY_FILE = "activity.json"

# Standart sozlamalar
DEFAULT_SETTINGS = {
    "language": "uz",
    "theme": "light",
    "color_scheme": "blue",
    "date_format": "dd.mm.yyyy",
    "time_format": "24",
    "system_name": "Smart Mahallah"
}

# Ma'lumotlarni yuklash funksiyalari
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"📊 Ma'lumotlar yuklandi: {len(data)} ta viloyat")
                return data
        else:
            print("🆕 Yangi ma'lumotlar bazasi yaratildi")
            initial_data = {}
            save_data(initial_data)
            return initial_data
    except Exception as e:
        print(f"❌ Ma'lumotlarni yuklashda xato: {e}")
        return {}

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Ma'lumotlar saqlandi: {len(data)} ta viloyat")
        return True
    except Exception as e:
        print(f"❌ Ma'lumotlarni saqlashda xato: {e}")
        return False

def load_admins():
    try:
        if os.path.exists(ADMINS_FILE):
            with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            default_admins = {
                "smartmahalla": {
                    "password": generate_password_hash("SmartMahalla1.0v"),
                    "role": "super_admin",
                    "email": "admin@mahallah.uz",
                    "phone": "+998933320335",
                    "created_at": datetime.now().isoformat(),
                    "last_login": None,
                    "is_active": True
                }
            }
            save_admins(default_admins)
            return default_admins
    except Exception as e:
        print(f"❌ Adminlarni yuklashda xato: {e}")
        return {}

def save_admins(admins):
    try:
        with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
            json.dump(admins, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ Adminlarni saqlashda xato: {e}")
        return False

def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                for key, value in DEFAULT_SETTINGS.items():
                    if key not in settings:
                        settings[key] = value
                return settings
        else:
            save_settings(DEFAULT_SETTINGS)
            return DEFAULT_SETTINGS
    except Exception as e:
        print(f"❌ Sozlamalarni yuklashda xato: {e}")
        return DEFAULT_SETTINGS

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ Sozlamalarni saqlashda xato: {e}")
        return False

def load_activity():
    try:
        if os.path.exists(ACTIVITY_FILE):
            with open(ACTIVITY_FILE, 'r', encoding='utf-8') as f:
                activities = json.load(f)
                # Faqat oxirgi 50 ta faoliyatni qaytaramiz
                return activities[-50:]
        else:
            return []
    except Exception as e:
        print(f"❌ Faoliyatni yuklashda xato: {e}")
        return []

def save_activity(activities):
    try:
        with open(ACTIVITY_FILE, 'w', encoding='utf-8') as f:
            json.dump(activities, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ Faoliyatni saqlashda xato: {e}")
        return False

def add_activity(action, details, username):
    activities = load_activity()
    activities.append({
        "action": action,
        "details": details,
        "username": username,
        "timestamp": datetime.now().isoformat(),
        "time_display": datetime.now().strftime("%H:%M"),
        "date_display": datetime.now().strftime("%d.%m.%Y")
    })
    if len(activities) > 50:
        activities = activities[-50:]
    save_activity(activities)

# Flask admin panel
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'smart-mahallah-secret-key-2024')
app.config['SESSION_TYPE'] = 'filesystem'

# Til matnlari
TEXTS = {
    'uz': {
        'dashboard': 'Boshqaruv paneli',
        'regions': 'Viloyatlar',
        'districts': 'Tumanlar va Shaharlar',
        'neighborhoods': 'MFYlar',
        'positions': 'Lavozimlar',
        'reports': 'Hisobotlar',
        'settings': 'Sozlamalar',
        'activity': 'Faoliyat',
        'logout': 'Chiqish',
        'welcome': 'Xush kelibsiz',
        'total_regions': 'Viloyatlar',
        'total_districts': 'Tumanlar/Shaharlar',
        'total_neighborhoods': 'MFYlar',
        'active_admins': 'Faol adminlar',
        'system_status': 'Tizim holati',
        'quick_actions': 'Tezkor amallar',
        'add_region': 'Viloyat qo\'shish',
        'add_district': 'Tuman/Shahar qo\'shish',
        'add_neighborhood': 'MFY qo\'shish',
        'add_staff': 'Xodim qo\'shish',
        'system_online': 'Tizim onlayn',
        'all_services_work': 'Barcha xizmatlar ishlayapti',
        'edit': 'Tahrirlash',
        'delete': 'O\'chirish',
        'save': 'Saqlash',
        'cancel': 'Bekor qilish',
        'search': 'Qidirish',
        'export': 'Eksport qilish',
        'backup': 'Zaxira nusxa',
        'statistics': 'Statistika',
        'profile_settings': 'Profil sozlamalari',
        'language_settings': 'Til sozlamalari',
        'security_settings': 'Xavfsizlik sozlamalari',
        'admin_management': 'Adminlar boshqaruvi',
        'system_settings': 'Tizim sozlamalari',
        'view_staff': 'Xodimlarni ko\'rish',
        'staff_list': 'Xodimlar ro\'yxati',
        'add_new_staff': 'Yangi xodim qo\'shish'
    },
    'ru': {
        'dashboard': 'Панель управления',
        'regions': 'Регионы',
        'districts': 'Районы и Города',
        'neighborhoods': 'МФЙ',
        'positions': 'Должности',
        'reports': 'Отчеты',
        'settings': 'Настройки',
        'activity': 'Активность',
        'logout': 'Выйти',
        'welcome': 'Добро пожаловать',
        'total_users': 'Всего пользователей',
        'total_regions': 'Регионы',
        'total_districts': 'Районы/Города',
        'total_neighborhoods': 'МФЙ',
        'active_admins': 'Активные админы',
        'system_status': 'Статус системы',
        'quick_actions': 'Быстрые действия',
        'add_region': 'Добавить регион',
        'add_district': 'Добавить район/город',
        'add_neighborhood': 'Добавить МФЙ',
        'add_staff': 'Добавить сотрудника',
        'system_online': 'Система онлайн',
        'all_services_work': 'Все сервисы работают',
        'edit': 'Редактировать',
        'delete': 'Удалить',
        'save': 'Сохранить',
        'cancel': 'Отмена',
        'search': 'Поиск',
        'export': 'Экспорт',
        'backup': 'Резервная копия',
        'statistics': 'Статистика',
        'profile_settings': 'Настройки профиля',
        'language_settings': 'Языковые настройки',
        'security_settings': 'Настройки безопасности',
        'admin_management': 'Управление админами',
        'system_settings': 'Системные настройки',
        'view_staff': 'Просмотр сотрудников',
        'staff_list': 'Список сотрудников',
        'add_new_staff': 'Добавить нового сотрудника'
    },
    'en': {
        'dashboard': 'Dashboard',
        'regions': 'Regions',
        'districts': 'Districts and Cities',
        'neighborhoods': 'Neighborhoods',
        'positions': 'Positions',
        'reports': 'Reports',
        'settings': 'Settings',
        'activity': 'Activity',
        'logout': 'Logout',
        'welcome': 'Welcome',
        'total_users': 'Total Users',
        'total_regions': 'Regions',
        'total_districts': 'Districts/Cities',
        'total_neighborhoods': 'Neighborhoods',
        'active_admins': 'Active Admins',
        'system_status': 'System Status',
        'quick_actions': 'Quick Actions',
        'add_region': 'Add Region',
        'add_district': 'Add District/City',
        'add_neighborhood': 'Add Neighborhood',
        'add_staff': 'Add Staff',
        'system_online': 'System Online',
        'all_services_work': 'All services work',
        'edit': 'Edit',
        'delete': 'Delete',
        'save': 'Save',
        'cancel': 'Cancel',
        'search': 'Search',
        'export': 'Export',
        'backup': 'Backup',
        'statistics': 'Statistics',
        'profile_settings': 'Profile Settings',
        'language_settings': 'Language Settings',
        'security_settings': 'Security Settings',
        'admin_management': 'Admin Management',
        'system_settings': 'System Settings',
        'view_staff': 'View Staff',
        'staff_list': 'Staff List',
        'add_new_staff': 'Add New Staff'
    }
}

# Login tizimi
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admins = load_admins()
        
        if username in admins and admins[username]['is_active']:
            if check_password_hash(admins[username]['password'], password):
                session['logged_in'] = True
                session['username'] = username
                session['role'] = admins[username]['role']
                
                settings = load_settings()
                session['language'] = settings.get('language', 'uz')
                
                add_activity("Tizimga kirish", f"{username} tizimga kirdi", username)
                
                admins[username]['last_login'] = datetime.now().isoformat()
                save_admins(admins)
                
                return redirect(url_for('admin_dashboard'))
        
        return render_template('login.html', error="Login yoki parol noto'g'ri")
    
    return render_template('login.html')

@app.route('/admin/logout')
def logout():
    if 'username' in session:
        add_activity("Tizimdan chiqish", f"{session['username']} tizimdan chiqdi", session['username'])
    session.clear()
    return redirect(url_for('login'))

# Statistika hisoblash
def calculate_stats(data):
    total_users = 0
    total_regions = len(data)
    total_districts = 0
    total_neighborhoods = 0
    total_staff = 0
    
    for region in data.values():
        total_districts += len(region.get('tumanlar', {}))
        for district in region.get('tumanlar', {}).values():
            total_neighborhoods += len(district.get('mfylar', {}))
            for neighborhood in district.get('mfylar', {}).values():
                if 'foydalanuvchilar_soni' in neighborhood:
                    try:
                        total_users += int(neighborhood['foydalanuvchilar_soni'])
                    except (ValueError, TypeError):
                        pass
                if 'xodimlar' in neighborhood:
                    for staff in neighborhood['xodimlar'].values():
                        if staff.get('ism') and staff['ism'].strip():
                            total_staff += 1
    
    return {
        'total_users': total_users,
        'total_regions': total_regions,
        'total_districts': total_districts,
        'total_neighborhoods': total_neighborhoods,
        'total_staff': total_staff
    }

# Asosiy route'lar


@app.route('/admin')
@login_required
def admin_dashboard():
    DATA = load_data()
    stats = calculate_stats(DATA)
    language = session.get('language', 'uz')
    activities = load_activity()[-10:]  # Faqat oxirgi 10 ta faoliyat
    
    admins = load_admins()
    active_admins = sum(1 for admin in admins.values() if admin.get('is_active', False))
    
    return render_template('admin_dashboard.html', 
                        data=DATA, 
                        stats=stats, 
                        username=session.get('username'),
                        now=datetime.now().strftime('%H:%M'),
                        texts=TEXTS[language],
                        active_admins=active_admins,
                        activities=activities,
                        language=language)

@app.route('/admin/viloyatlar')
@login_required
def admin_viloyatlar():
    DATA = load_data()
    stats = calculate_stats(DATA)
    language = session.get('language', 'uz')
    
    return render_template('viloyatlar.html', 
                        data=DATA, 
                        stats=stats, 
                        username=session.get('username'),
                        texts=TEXTS[language],
                        language=language)

@app.route('/admin/tumanlar')
@login_required
def admin_tumanlar():
    DATA = load_data()
    stats = calculate_stats(DATA)
    language = session.get('language', 'uz')
    
    tumanlar_list = []
    for viloyat_nomi, viloyat in DATA.items():
        for tuman_nomi, tuman in viloyat.get('tumanlar', {}).items():
            mfy_soni = len(tuman.get('mfylar', {}))
            tumanlar_list.append({
                'viloyat': viloyat_nomi,
                'tuman': tuman_nomi,
                'tuman_turi': tuman.get('type', 'tuman'),
                'mfy_soni': mfy_soni
            })
    
    return render_template('tumanlar.html', 
                        data=DATA, 
                        stats=stats, 
                        tumanlar=tumanlar_list,
                        username=session.get('username'),
                        texts=TEXTS[language],
                        language=language)

@app.route('/admin/mfylar')
@login_required
def admin_mfylar():
    DATA = load_data()
    stats = calculate_stats(DATA)
    language = session.get('language', 'uz')
    
    mfylar_list = []
    for viloyat_nomi, viloyat in DATA.items():
        for tuman_nomi, tuman in viloyat.get('tumanlar', {}).items():
            for mfy_nomi, mfy in tuman.get('mfylar', {}).items():
                xodim_soni = len([x for x in mfy.get('xodimlar', {}).values() if x.get('ism')])
                mfylar_list.append({
                    'viloyat': viloyat_nomi,
                    'tuman': tuman_nomi,
                    'mfy': mfy_nomi,
                    'foydalanuvchilar': mfy.get('foydalanuvchilar_soni', '0'),
                    'xodim_soni': xodim_soni,
                    'holat': mfy.get('holat', 'faol')
                })
    
    return render_template('mfylar.html', 
                        data=DATA, 
                        stats=stats, 
                        mfylar=mfylar_list,
                        username=session.get('username'),
                        texts=TEXTS[language],
                        language=language)

@app.route('/admin/lavozimlar')
@login_required
def admin_lavozimlar():
    DATA = load_data()
    stats = calculate_stats(DATA)
    language = session.get('language', 'uz')
    
    lavozimlar = {}
    xodimlar_list = []
    
    for viloyat_nomi, viloyat in DATA.items():
        for tuman_nomi, tuman in viloyat.get('tumanlar', {}).items():
            for mfy_nomi, mfy in tuman.get('mfylar', {}).items():
                for lavozim, xodim in mfy.get('xodimlar', {}).items():
                    if lavozim not in lavozimlar:
                        lavozimlar[lavozim] = 0
                    if xodim.get('ism') and xodim['ism'].strip():
                        lavozimlar[lavozim] += 1
                        xodimlar_list.append({
                            'viloyat': viloyat_nomi,
                            'tuman': tuman_nomi,
                            'mfy': mfy_nomi,
                            'lavozim': lavozim,
                            'ism': xodim['ism'],
                            'telefon': xodim.get('telefon', ''),
                            'email': xodim.get('email', ''),
                            'holat': xodim.get('holat', 'faol')
                        })
    
    return render_template('lavozimlar.html', 
                        data=DATA, 
                        stats=stats, 
                        lavozimlar=lavozimlar,
                        xodimlar=xodimlar_list,
                        username=session.get('username'),
                        texts=TEXTS[language],
                        language=language)

@app.route('/admin/sozlamalar')
@login_required
def admin_sozlamalar():
    DATA = load_data()
    stats = calculate_stats(DATA)
    language = session.get('language', 'uz')
    settings = load_settings()
    admins = load_admins()
    
    active_admins = sum(1 for admin in admins.values() if admin.get('is_active', False))
    
    return render_template('sozlamalar.html', 
                        data=DATA, 
                        stats=stats, 
                        username=session.get('username'),
                        settings=settings,
                        admins=admins,
                        active_admins=active_admins,
                        texts=TEXTS[language],
                        language=language)

@app.route('/admin/faoliyat')
@login_required
def admin_faoliyat():
    DATA = load_data()
    stats = calculate_stats(DATA)
    language = session.get('language', 'uz')
    activities = load_activity()
    
    return render_template('faoliyat.html', 
                        data=DATA, 
                        stats=stats, 
                        username=session.get('username'),
                        texts=TEXTS[language],
                        activities=activities,
                        language=language)

@app.route('/admin/xodimlar')
@login_required
def admin_xodimlar():
    DATA = load_data()
    stats = calculate_stats(DATA)
    language = session.get('language', 'uz')
    
    # Tanlangan MFY bo'yicha xodimlarni olish
    viloyat = request.args.get('viloyat', '')
    tuman = request.args.get('tuman', '')
    mahalla = request.args.get('mahalla', '')
    
    xodimlar = {}
    if viloyat and tuman and mahalla:
        if (viloyat in DATA and 
            tuman in DATA[viloyat]['tumanlar'] and 
            mahalla in DATA[viloyat]['tumanlar'][tuman]['mfylar']):
            xodimlar = DATA[viloyat]['tumanlar'][tuman]['mfylar'][mahalla]['xodimlar']
    
    return render_template('xodimlar.html', 
                        data=DATA, 
                        stats=stats, 
                        username=session.get('username'),
                        texts=TEXTS[language],
                        xodimlar=xodimlar,
                        selected_viloyat=viloyat,
                        selected_tuman=tuman,
                        selected_mahalla=mahalla,
                        language=language)

# API Route'lari
@app.route('/admin/add_viloyat', methods=['POST'])
@login_required
def add_viloyat():
    try:
        DATA = load_data()
        viloyat_nomi = request.json.get('viloyat_nomi', '').strip()
        viloyat_turi = request.json.get('viloyat_turi', 'viloyat')
        
        if not viloyat_nomi:
            return jsonify({'success': False, 'message': 'Viloyat nomi bo\'sh'})
            
        if viloyat_nomi in DATA:
            return jsonify({'success': False, 'message': 'Bu viloyat allaqachon mavjud'})
        
        DATA[viloyat_nomi] = {
            "type": viloyat_turi,
            "tumanlar": {}
        }
        success = save_data(DATA)
        
        if success:
            add_activity("Yangi viloyat qo'shildi", f"{viloyat_nomi} qo'shildi", session.get('username'))
            return jsonify({'success': True, 'message': f'"{viloyat_nomi}" muvaffaqiyatli qoʻshildi!'})
        else:
            return jsonify({'success': False, 'message': 'Ma\'lumotlarni saqlashda xato'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server xatosi: {e}'})

@app.route('/admin/add_tuman', methods=['POST'])
@login_required
def add_tuman():
    try:
        DATA = load_data()
        viloyat_nomi = request.json.get('viloyat_nomi', '').strip()
        tuman_nomi = request.json.get('tuman_nomi', '').strip()
        tuman_turi = request.json.get('tuman_turi', 'tuman')
        
        if not viloyat_nomi or not tuman_nomi:
            return jsonify({'success': False, 'message': 'Viloyat yoki tuman nomi bo\'sh'})
            
        if viloyat_nomi not in DATA:
            return jsonify({'success': False, 'message': 'Bunday viloyat mavjud emas'})
            
        if tuman_nomi in DATA[viloyat_nomi]['tumanlar']:
            return jsonify({'success': False, 'message': 'Bu tuman/shahar allaqachon mavjud'})
        
        DATA[viloyat_nomi]['tumanlar'][tuman_nomi] = {
            "type": tuman_turi,
            "mfylar": {}
        }
        success = save_data(DATA)
        
        if success:
            add_activity("Yangi tuman/shahar qo'shildi", f"{viloyat_nomi}, {tuman_nomi} ({tuman_turi}) qo'shildi", session.get('username'))
            return jsonify({'success': True, 'message': f'"{tuman_nomi}" {tuman_turi} muvaffaqiyatli qoʻshildi!'})
        else:
            return jsonify({'success': False, 'message': 'Ma\'lumotlarni saqlashda xato'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server xatosi: {e}'})

@app.route('/admin/add_mahalla', methods=['POST'])
@login_required
def add_mahalla():
    try:
        DATA = load_data()
        viloyat_nomi = request.json.get('viloyat_nomi', '').strip()
        tuman_nomi = request.json.get('tuman_nomi', '').strip()
        mahalla_nomi = request.json.get('mahalla_nomi', '').strip()
        
        if not all([viloyat_nomi, tuman_nomi, mahalla_nomi]):
            return jsonify({'success': False, 'message': 'Barcha maydonlarni to\'ldiring'})
            
        if (viloyat_nomi not in DATA or 
            tuman_nomi not in DATA[viloyat_nomi]['tumanlar']):
            return jsonify({'success': False, 'message': 'Bunday viloyat yoki tuman mavjud emas'})
            
        if mahalla_nomi in DATA[viloyat_nomi]['tumanlar'][tuman_nomi]['mfylar']:
            return jsonify({'success': False, 'message': 'Bu MFY allaqachon mavjud'})
        
        DATA[viloyat_nomi]['tumanlar'][tuman_nomi]['mfylar'][mahalla_nomi] = {
            "xodimlar": {
                "hokim": {"ism": "", "telefon": "", "email": "", "holat": "faol"},
                "2-sektor_rahbari": {"ism": "", "telefon": "", "email": "", "holat": "faol"},
                "mfy_raisi": {"ism": "", "telefon": "", "email": "", "holat": "faol"},
                "iib_inspektori": {"ism": "", "telefon": "", "email": "", "holat": "faol"},
                "hokim_yordamchisi": {"ism": "", "telefon": "", "email": "", "holat": "faol"},
                "yoshlar_yetakchisi": {"ism": "", "telefon": "", "email": "", "holat": "faol"}
            },
            "foydalanuvchilar_soni": "0",
            "yaratilgan_vaqt": datetime.now().isoformat(),
            "holat": "faol"
        }
        success = save_data(DATA)
        
        if success:
            add_activity("Yangi MFY qo'shildi", f"{viloyat_nomi}, {tuman_nomi}, {mahalla_nomi} MFYsi qo'shildi", session.get('username'))
            return jsonify({'success': True, 'message': f'"{mahalla_nomi}" MFY muvaffaqiyatli qoʻshildi!'})
        else:
            return jsonify({'success': False, 'message': 'Ma\'lumotlarni saqlashda xato'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server xatosi: {e}'})

@app.route('/admin/add_xodim', methods=['POST'])
@login_required
def add_xodim():
    try:
        DATA = load_data()
        viloyat_nomi = request.json.get('viloyat_nomi', '').strip()
        tuman_nomi = request.json.get('tuman_nomi', '').strip()
        mahalla_nomi = request.json.get('mahalla_nomi', '').strip()
        lavozim = request.json.get('lavozim', '').strip()
        ism = request.json.get('ism', '').strip()
        telefon = request.json.get('telefon', '').strip()
        email = request.json.get('email', '').strip()
        
        if not all([viloyat_nomi, tuman_nomi, mahalla_nomi, lavozim, ism, telefon]):
            return jsonify({'success': False, 'message': 'Barcha maydonlarni to\'ldiring'})
            
        if (viloyat_nomi not in DATA or 
            tuman_nomi not in DATA[viloyat_nomi]['tumanlar'] or 
            mahalla_nomi not in DATA[viloyat_nomi]['tumanlar'][tuman_nomi]['mfylar']):
            return jsonify({'success': False, 'message': 'MFY topilmadi'})
        
        DATA[viloyat_nomi]['tumanlar'][tuman_nomi]['mfylar'][mahalla_nomi]['xodimlar'][lavozim] = {
            "ism": ism,
            "telefon": telefon,
            "email": email,
            "holat": "faol"
        }
        success = save_data(DATA)
        
        if success:
            add_activity("Xodim qo'shildi", f"{viloyat_nomi}, {tuman_nomi}, {mahalla_nomi} - {lavozim}: {ism}", session.get('username'))
            return jsonify({'success': True, 'message': f'Xodim muvaffaqiyatli qoʻshildi!'})
        else:
            return jsonify({'success': False, 'message': 'Ma\'lumotlarni saqlashda xato'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server xatosi: {e}'})

# Tahrirlash API'lari
@app.route('/admin/update_viloyat', methods=['POST'])
@login_required
def update_viloyat():
    try:
        DATA = load_data()
        old_viloyat_nomi = request.json.get('old_viloyat_nomi', '').strip()
        new_viloyat_nomi = request.json.get('new_viloyat_nomi', '').strip()
        viloyat_turi = request.json.get('viloyat_turi', 'viloyat')
        
        if not old_viloyat_nomi or not new_viloyat_nomi:
            return jsonify({'success': False, 'message': 'Viloyat nomlari bo\'sh'})
            
        if old_viloyat_nomi not in DATA:
            return jsonify({'success': False, 'message': 'Viloyat topilmadi'})
        
        if old_viloyat_nomi != new_viloyat_nomi and new_viloyat_nomi in DATA:
            return jsonify({'success': False, 'message': 'Yangi viloyat nomi allaqachon mavjud'})
        
        # Viloyatni yangilash
        viloyat_data = DATA.pop(old_viloyat_nomi)
        viloyat_data['type'] = viloyat_turi
        DATA[new_viloyat_nomi] = viloyat_data
        
        success = save_data(DATA)
        
        if success:
            add_activity("Viloyat tahrirlandi", f"{old_viloyat_nomi} -> {new_viloyat_nomi} ({viloyat_turi})", session.get('username'))
            return jsonify({'success': True, 'message': f'Viloyat muvaffaqiyatli yangilandi!'})
        else:
            return jsonify({'success': False, 'message': 'Ma\'lumotlarni saqlashda xato'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server xatosi: {e}'})

@app.route('/admin/update_tuman', methods=['POST'])
@login_required
def update_tuman():
    try:
        DATA = load_data()
        old_viloyat_nomi = request.json.get('old_viloyat_nomi', '').strip()
        old_tuman_nomi = request.json.get('old_tuman_nomi', '').strip()
        new_viloyat_nomi = request.json.get('viloyat_nomi', '').strip()
        new_tuman_nomi = request.json.get('new_tuman_nomi', '').strip()
        tuman_turi = request.json.get('tuman_turi', 'tuman')
        
        if not all([old_viloyat_nomi, old_tuman_nomi, new_viloyat_nomi, new_tuman_nomi]):
            return jsonify({'success': False, 'message': 'Barcha maydonlarni to\'ldiring'})
        
        if old_viloyat_nomi not in DATA or old_tuman_nomi not in DATA[old_viloyat_nomi]['tumanlar']:
            return jsonify({'success': False, 'message': 'Tuman topilmadi'})
        
        # Agar viloyat o'zgartirilgan bo'lsa
        if old_viloyat_nomi != new_viloyat_nomi:
            if new_viloyat_nomi not in DATA:
                return jsonify({'success': False, 'message': 'Yangi viloyat topilmadi'})
            
            # Tuman ma'lumotlarini yangi viloyatga ko'chirish
            tuman_data = DATA[old_viloyat_nomi]['tumanlar'].pop(old_tuman_nomi)
            DATA[new_viloyat_nomi]['tumanlar'][new_tuman_nomi] = tuman_data
        else:
            # Faqat tuman nomi o'zgartirilgan bo'lsa
            if old_tuman_nomi != new_tuman_nomi:
                if new_tuman_nomi in DATA[old_viloyat_nomi]['tumanlar']:
                    return jsonify({'success': False, 'message': 'Bu tuman nomi allaqachon mavjud'})
                
                tuman_data = DATA[old_viloyat_nomi]['tumanlar'].pop(old_tuman_nomi)
                DATA[old_viloyat_nomi]['tumanlar'][new_tuman_nomi] = tuman_data
        
        # Tuman turini yangilash
        DATA[new_viloyat_nomi]['tumanlar'][new_tuman_nomi]['type'] = tuman_turi
        
        success = save_data(DATA)
        
        if success:
            add_activity("Tuman yangilandi", 
                        f"{old_viloyat_nomi}, {old_tuman_nomi} -> {new_viloyat_nomi}, {new_tuman_nomi} ({tuman_turi})", 
                        session.get('username'))
            return jsonify({'success': True, 'message': f'Tuman muvaffaqiyatli yangilandi!'})
        else:
            return jsonify({'success': False, 'message': 'Ma\'lumotlarni saqlashda xato'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server xatosi: {e}'})

@app.route('/admin/update_mahalla', methods=['POST'])
@login_required
def update_mahalla():
    try:
        DATA = load_data()
        old_viloyat_nomi = request.json.get('old_viloyat_nomi', '').strip()
        old_tuman_nomi = request.json.get('old_tuman_nomi', '').strip()
        old_mahalla_nomi = request.json.get('old_mahalla_nomi', '').strip()
        new_viloyat_nomi = request.json.get('viloyat_nomi', '').strip()
        new_tuman_nomi = request.json.get('tuman_nomi', '').strip()
        new_mahalla_nomi = request.json.get('new_mahalla_nomi', '').strip()
        
        if not all([old_viloyat_nomi, old_tuman_nomi, old_mahalla_nomi, new_viloyat_nomi, new_tuman_nomi, new_mahalla_nomi]):
            return jsonify({'success': False, 'message': 'Barcha maydonlarni to\'ldiring'})
        
        if (old_viloyat_nomi not in DATA or 
            old_tuman_nomi not in DATA[old_viloyat_nomi]['tumanlar'] or 
            old_mahalla_nomi not in DATA[old_viloyat_nomi]['tumanlar'][old_tuman_nomi]['mfylar']):
            return jsonify({'success': False, 'message': 'MFY topilmadi'})
        
        # MFY ma'lumotlarini olish
        mahalla_data = DATA[old_viloyat_nomi]['tumanlar'][old_tuman_nomi]['mfylar'].pop(old_mahalla_nomi)
        
        # Yangi joyga qo'shish
        if new_viloyat_nomi not in DATA:
            return jsonify({'success': False, 'message': 'Yangi viloyat topilmadi'})
        
        if new_tuman_nomi not in DATA[new_viloyat_nomi]['tumanlar']:
            return jsonify({'success': False, 'message': 'Yangi tuman topilmadi'})
        
        if new_mahalla_nomi in DATA[new_viloyat_nomi]['tumanlar'][new_tuman_nomi]['mfylar']:
            return jsonify({'success': False, 'message': 'Bu MFY nomi allaqachon mavjud'})
        
        DATA[new_viloyat_nomi]['tumanlar'][new_tuman_nomi]['mfylar'][new_mahalla_nomi] = mahalla_data
        
        success = save_data(DATA)
        
        if success:
            add_activity("MFY yangilandi", 
                        f"{old_viloyat_nomi}, {old_tuman_nomi}, {old_mahalla_nomi} -> {new_viloyat_nomi}, {new_tuman_nomi}, {new_mahalla_nomi}", 
                        session.get('username'))
            return jsonify({'success': True, 'message': f'MFY muvaffaqiyatli yangilandi!'})
        else:
            return jsonify({'success': False, 'message': 'Ma\'lumotlarni saqlashda xato'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server xatosi: {e}'})

@app.route('/admin/update_xodim', methods=['POST'])
@login_required
def update_xodim():
    try:
        DATA = load_data()
        viloyat_nomi = request.json.get('viloyat_nomi', '').strip()
        tuman_nomi = request.json.get('tuman_nomi', '').strip()
        mahalla_nomi = request.json.get('mahalla_nomi', '').strip()
        lavozim_old = request.json.get('lavozim_old', '').strip()
        lavozim = request.json.get('lavozim', '').strip()
        ism = request.json.get('ism', '').strip()
        telefon = request.json.get('telefon', '').strip()
        email = request.json.get('email', '').strip()
        holat = request.json.get('holat', 'faol')
        
        if not all([viloyat_nomi, tuman_nomi, mahalla_nomi, lavozim, ism, telefon]):
            return jsonify({'success': False, 'message': 'Barcha maydonlarni to\'ldiring'})
            
        if (viloyat_nomi not in DATA or 
            tuman_nomi not in DATA[viloyat_nomi]['tumanlar'] or 
            mahalla_nomi not in DATA[viloyat_nomi]['tumanlar'][tuman_nomi]['mfylar']):
            return jsonify({'success': False, 'message': 'MFY topilmadi'})
        
        # Agar lavozim o'zgartirilgan bo'lsa
        if lavozim_old and lavozim_old != lavozim:
            if lavozim_old in DATA[viloyat_nomi]['tumanlar'][tuman_nomi]['mfylar'][mahalla_nomi]['xodimlar']:
                # Eski lavozimni o'chirish
                del DATA[viloyat_nomi]['tumanlar'][tuman_nomi]['mfylar'][mahalla_nomi]['xodimlar'][lavozim_old]
        
        # Yangi ma'lumotlarni saqlash
        DATA[viloyat_nomi]['tumanlar'][tuman_nomi]['mfylar'][mahalla_nomi]['xodimlar'][lavozim] = {
            "ism": ism,
            "telefon": telefon,
            "email": email,
            "holat": holat
        }
        success = save_data(DATA)
        
        if success:
            add_activity("Xodim tahrirlandi", f"{viloyat_nomi}, {tuman_nomi}, {mahalla_nomi} - {lavozim}: {ism}", session.get('username'))
            return jsonify({'success': True, 'message': f'Xodim muvaffaqiyatli tahrirlandi!'})
        else:
            return jsonify({'success': False, 'message': 'Ma\'lumotlarni saqlashda xato'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server xatosi: {e}'})

# O'chirish API'lari
@app.route('/admin/delete_viloyat', methods=['POST'])
@login_required
def delete_viloyat():
    try:
        DATA = load_data()
        viloyat_nomi = request.json.get('viloyat_nomi', '').strip()
        
        if not viloyat_nomi:
            return jsonify({'success': False, 'message': 'Viloyat nomi berilmagan'})
            
        if viloyat_nomi not in DATA:
            return jsonify({'success': False, 'message': 'Viloyat topilmadi'})
        
        del DATA[viloyat_nomi]
        success = save_data(DATA)
        
        if success:
            add_activity("Viloyat o'chirildi", f"{viloyat_nomi} viloyati o'chirildi", session.get('username'))
            return jsonify({'success': True, 'message': f'"{viloyat_nomi}" o\'chirildi'})
        else:
            return jsonify({'success': False, 'message': 'Saqlashda xato'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Xato: {e}'})

@app.route('/admin/delete_tuman', methods=['POST'])
@login_required
def delete_tuman():
    try:
        DATA = load_data()
        viloyat_nomi = request.json.get('viloyat_nomi', '').strip()
        tuman_nomi = request.json.get('tuman_nomi', '').strip()
        
        if not all([viloyat_nomi, tuman_nomi]):
            return jsonify({'success': False, 'message': 'Viloyat yoki tuman nomi berilmagan'})
            
        if viloyat_nomi not in DATA or tuman_nomi not in DATA[viloyat_nomi]['tumanlar']:
            return jsonify({'success': False, 'message': 'Tuman topilmadi'})
        
        # MFYlar sonini hisoblash
        mfy_count = len(DATA[viloyat_nomi]['tumanlar'][tuman_nomi].get('mfylar', {}))
        
        del DATA[viloyat_nomi]['tumanlar'][tuman_nomi]
        success = save_data(DATA)
        
        if success:
            add_activity("Tuman o'chirildi", 
                        f"{viloyat_nomi}, {tuman_nomi} ({mfy_count} ta MFY bilan)", 
                        session.get('username'))
            return jsonify({'success': True, 'message': f'"{tuman_nomi}" tumani {mfy_count} ta MFY bilan o\'chirildi'})
        else:
            return jsonify({'success': False, 'message': 'Saqlashda xato'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Xato: {e}'})

@app.route('/admin/delete_mahalla', methods=['POST'])
@login_required
def delete_mahalla():
    try:
        DATA = load_data()
        viloyat_nomi = request.json.get('viloyat_nomi', '').strip()
        tuman_nomi = request.json.get('tuman_nomi', '').strip()
        mahalla_nomi = request.json.get('mahalla_nomi', '').strip()
        
        if not all([viloyat_nomi, tuman_nomi, mahalla_nomi]):
            return jsonify({'success': False, 'message': 'Barcha maydonlar to\'ldirilmagan'})
            
        if (viloyat_nomi not in DATA or 
            tuman_nomi not in DATA[viloyat_nomi]['tumanlar'] or 
            mahalla_nomi not in DATA[viloyat_nomi]['tumanlar'][tuman_nomi]['mfylar']):
            return jsonify({'success': False, 'message': 'MFY topilmadi'})
        
        del DATA[viloyat_nomi]['tumanlar'][tuman_nomi]['mfylar'][mahalla_nomi]
        success = save_data(DATA)
        
        if success:
            add_activity("MFY o'chirildi", f"{viloyat_nomi}, {tuman_nomi}, {mahalla_nomi} MFYsi o'chirildi", session.get('username'))
            return jsonify({'success': True, 'message': f'"{mahalla_nomi}" MFY o\'chirildi'})
        else:
            return jsonify({'success': False, 'message': 'Saqlashda xato'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Xato: {e}'})

@app.route('/admin/delete_xodim', methods=['POST'])
@login_required
def delete_xodim():
    try:
        DATA = load_data()
        viloyat_nomi = request.json.get('viloyat_nomi', '').strip()
        tuman_nomi = request.json.get('tuman_nomi', '').strip()
        mahalla_nomi = request.json.get('mahalla_nomi', '').strip()
        lavozim = request.json.get('lavozim', '').strip()
        
        if not all([viloyat_nomi, tuman_nomi, mahalla_nomi, lavozim]):
            return jsonify({'success': False, 'message': 'Barcha maydonlar to\'ldirilmagan'})
            
        if (viloyat_nomi not in DATA or 
            tuman_nomi not in DATA[viloyat_nomi]['tumanlar'] or 
            mahalla_nomi not in DATA[viloyat_nomi]['tumanlar'][tuman_nomi]['mfylar'] or
            lavozim not in DATA[viloyat_nomi]['tumanlar'][tuman_nomi]['mfylar'][mahalla_nomi]['xodimlar']):
            return jsonify({'success': False, 'message': 'Xodim topilmadi'})
        
        xodim_ismi = DATA[viloyat_nomi]['tumanlar'][tuman_nomi]['mfylar'][mahalla_nomi]['xodimlar'][lavozim].get('ism', '')
        
        # Xodimni butunlay o'chirish
        del DATA[viloyat_nomi]['tumanlar'][tuman_nomi]['mfylar'][mahalla_nomi]['xodimlar'][lavozim]
        
        success = save_data(DATA)
        
        if success:
            add_activity("Xodim o'chirildi", f"{viloyat_nomi}, {tuman_nomi}, {mahalla_nomi} - {lavozim}: {xodim_ismi}", session.get('username'))
            return jsonify({'success': True, 'message': f'Xodim o\'chirildi!'})
        else:
            return jsonify({'success': False, 'message': 'Ma\'lumotlarni saqlashda xato'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Xato: {e}'})

# Sozlamalar API'lari
@app.route('/admin/update_password', methods=['POST'])
@login_required
def update_password():
    try:
        current_password = request.json.get('current_password', '')
        new_password = request.json.get('new_password', '')
        confirm_password = request.json.get('confirm_password', '')
        username = session.get('username')
        
        admins = load_admins()
        
        if username not in admins:
            return jsonify({'success': False, 'message': 'Foydalanuvchi topilmadi'})
        
        if not check_password_hash(admins[username]['password'], current_password):
            return jsonify({'success': False, 'message': 'Joriy parol noto\'g\'ri'})
        
        if new_password != confirm_password:
            return jsonify({'success': False, 'message': 'Yangi parollar mos kelmadi'})
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'Parol kamida 6 ta belgidan iborat bo\'lishi kerak'})
        
        admins[username]['password'] = generate_password_hash(new_password)
        success = save_admins(admins)
        
        if success:
            add_activity("Parol yangilandi", f"{username} parolini yangiladi", username)
            return jsonify({'success': True, 'message': 'Parol muvaffaqiyatli yangilandi!'})
        else:
            return jsonify({'success': False, 'message': 'Parolni saqlashda xato'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Xato: {e}'})

@app.route('/admin/update_username', methods=['POST'])
@login_required
def update_username():
    try:
        new_username = request.json.get('new_username', '').strip()
        password = request.json.get('password', '')
        current_username = session.get('username')
        
        if not new_username or not password:
            return jsonify({'success': False, 'message': 'Barcha maydonlarni to\'ldiring'})
        
        if len(new_username) < 3:
            return jsonify({'success': False, 'message': 'Login kamida 3 belgidan iborat bo\'lishi kerak'})
        
        admins = load_admins()
        
        if current_username not in admins:
            return jsonify({'success': False, 'message': 'Foydalanuvchi topilmadi'})
        
        if not check_password_hash(admins[current_username]['password'], password):
            return jsonify({'success': False, 'message': 'Parol noto\'g\'ri'})
        
        if new_username in admins and new_username != current_username:
            return jsonify({'success': False, 'message': 'Bu login allaqachon mavjud'})
        
        # Yangi username bilan admin ma'lumotlarini ko'chirish
        admins[new_username] = admins.pop(current_username)
        
        success = save_admins(admins)
        
        if success:
            session['username'] = new_username
            add_activity("Login o'zgartirildi", f"{current_username} -> {new_username}", new_username)
            return jsonify({'success': True, 'message': f'Login muvaffaqiyatli "{new_username}" ga o\'zgartirildi!'})
        else:
            return jsonify({'success': False, 'message': 'Loginni saqlashda xato'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Xato: {e}'})

@app.route('/admin/add_admin', methods=['POST'])
@login_required
def add_admin():
    try:
        if session.get('role') != 'super_admin':
            return jsonify({'success': False, 'message': 'Faqat super admin yangi admin qo\'sha oladi'})
        
        new_login = request.json.get('login', '').strip()
        new_password = request.json.get('password', '').strip()
        role = request.json.get('role', 'moderator').strip()
        email = request.json.get('email', '').strip()
        phone = request.json.get('phone', '').strip()
        
        if not new_login or not new_password:
            return jsonify({'success': False, 'message': 'Login va parol kiritilishi shart'})
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'Parol kamida 6 ta belgidan iborat bo\'lishi kerak'})
        
        admins = load_admins()
        
        if new_login in admins:
            return jsonify({'success': False, 'message': 'Bu login allaqachon mavjud'})
        
        admins[new_login] = {
            "password": generate_password_hash(new_password),
            "role": role,
            "email": email,
            "phone": phone,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "is_active": True
        }
        
        success = save_admins(admins)
        
        if success:
            add_activity("Yangi admin qo'shildi", f"{new_login} admin qo'shildi", session.get('username'))
            return jsonify({'success': True, 'message': f'Yangi admin "{new_login}" muvaffaqiyatli qo\'shildi!'})
        else:
            return jsonify({'success': False, 'message': 'Adminni saqlashda xato'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Xato: {e}'})

@app.route('/admin/delete_admin', methods=['POST'])
@login_required
def delete_admin():
    try:
        if session.get('role') != 'super_admin':
            return jsonify({'success': False, 'message': 'Faqat super admin adminlarni o\'chira oladi'})
        
        login = request.json.get('login', '').strip()
        current_username = session.get('username')
        
        if not login:
            return jsonify({'success': False, 'message': 'Login berilmagan'})
        
        if login == current_username:
            return jsonify({'success': False, 'message': 'O\'zingizni o\'chira olmaysiz'})
        
        admins = load_admins()
        
        if login not in admins:
            return jsonify({'success': False, 'message': 'Admin topilmadi'})
        
        del admins[login]
        success = save_admins(admins)
        
        if success:
            add_activity("Admin o'chirildi", f"{login} admini o'chirildi", current_username)
            return jsonify({'success': True, 'message': f'Admin "{login}" muvaffaqiyatli o\'chirildi!'})
        else:
            return jsonify({'success': False, 'message': 'Adminni o\'chirishda xato'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Xato: {e}'})

@app.route('/admin/change_language', methods=['POST'])
@login_required
def change_language():
    try:
        language = request.json.get('language', 'uz')
        if language in ['uz', 'ru', 'en']:
            session['language'] = language
            settings = load_settings()
            settings['language'] = language
            save_settings(settings)
            
            add_activity("Til o'zgartirildi", f"Til {language} ga o'zgartirildi", session.get('username'))
            return jsonify({'success': True, 'message': f'Til {language} ga o\'zgartirildi'})
        else:
            return jsonify({'success': False, 'message': 'Noto\'g\'ri til kodi'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Xato: {e}'})

# Qolgan API'lar
@app.route('/admin/get_tumanlar')
@login_required
def get_tumanlar():
    try:
        DATA = load_data()
        viloyat = request.args.get('viloyat', '').strip()
        
        if not viloyat or viloyat not in DATA:
            return jsonify([])
            
        tumans = list(DATA[viloyat]['tumanlar'].keys())
        return jsonify(tumans)
    except Exception as e:
        return jsonify([])

@app.route('/admin/get_mahallalar')
@login_required
def get_mahallalar():
    try:
        DATA = load_data()
        viloyat = request.args.get('viloyat', '').strip()
        tuman = request.args.get('tuman', '').strip()
        
        if not viloyat or not tuman or viloyat not in DATA or tuman not in DATA[viloyat]['tumanlar']:
            return jsonify([])
            
        mahallalar = list(DATA[viloyat]['tumanlar'][tuman]['mfylar'].keys())
        return jsonify(mahallalar)
    except Exception as e:
        return jsonify([])

@app.route('/admin/get_xodimlar')
@login_required
def get_xodimlar():
    try:
        DATA = load_data()
        viloyat = request.args.get('viloyat', '').strip()
        tuman = request.args.get('tuman', '').strip()
        mahalla = request.args.get('mahalla', '').strip()
        
        if not all([viloyat, tuman, mahalla]):
            return jsonify({})
            
        if (viloyat in DATA and 
            tuman in DATA[viloyat]['tumanlar'] and 
            mahalla in DATA[viloyat]['tumanlar'][tuman]['mfylar']):
            xodimlar = DATA[viloyat]['tumanlar'][tuman]['mfylar'][mahalla]['xodimlar']
            return jsonify(xodimlar)
        
        return jsonify({})
    except Exception as e:
        return jsonify({})

# 404 sahifasi
@app.errorhandler(404)
def not_found(error):
    language = session.get('language', 'uz') if session.get('logged_in') else 'uz'
    return render_template('404.html', 
                        language=language, 
                        texts=TEXTS.get(language, TEXTS['uz'])), 404

# Telegram bot qismi
def get_viloyatlar():
    DATA = load_data()
    return list(DATA.keys())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = f"👋 Assalomu alaykum, {user.first_name}!\n\n🏛️ *Smart Mahalla* botiga xush kelibsiz!\n\nViloyatingizni tanlang:"
    keyboard = []
    for v in get_viloyatlar():
        keyboard.append([InlineKeyboardButton(f"🏛️ {v}", callback_data=f"VIL|{v}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    DATA = load_data()
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split("|")

    if parts[0] == "VIL":
        viloyat = parts[1]
        tumans = list(DATA.get(viloyat, {}).get('tumanlar', {}).keys())
        if not tumans:
            keyboard = [[InlineKeyboardButton("🔙 Bosh sahifa", callback_data="BACK|HOME")]]
            await query.edit_message_text(
                f"❌ *{viloyat}* uchun hozircha tumanlar mavjud emas.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            return
        
        keyboard = []
        for t in tumans:
            mahalla_count = len(DATA[viloyat]['tumanlar'][t]['mfylar'])
            button_text = f"📍 {t} ({mahalla_count})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"TUM|{viloyat}|{t}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Bosh sahifa", callback_data="BACK|HOME")])
        
        await query.edit_message_text(
            text=f"🏛️ *{viloyat}*\n\n📍 Tumanlardan birini tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif parts[0] == "TUM":
        if len(parts) < 3:
            await query.edit_message_text("❌ Nimadir xato bo'ldi.")
            return
        viloyat, tuman = parts[1], parts[2]
        mahallalar = list(DATA.get(viloyat, {}).get('tumanlar', {}).get(tuman, {}).get('mfylar', {}).keys())
        
        if not mahallalar:
            keyboard = [
                [InlineKeyboardButton("🔙 Tumanlar", callback_data=f"VIL|{viloyat}")],
                [InlineKeyboardButton("🏠 Bosh sahifa", callback_data="BACK|HOME")]
            ]
            await query.edit_message_text(
                f"❌ *{tuman}* uchun hozircha mahallalar mavjud emas.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            return

        keyboard = []
        for m in mahallalar:
            user_count = DATA[viloyat]['tumanlar'][tuman]['mfylar'][m].get('foydalanuvchilar_soni', '0')
            button_text = f"🏘️ {m} ({user_count})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"MAH|{viloyat}|{tuman}|{m}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Viloyatlar", callback_data=f"VIL|{viloyat}")])
        keyboard.append([InlineKeyboardButton("🏠 Bosh sahifa", callback_data="BACK|HOME")])
        
        await query.edit_message_text(
            text=f"📍 *{viloyat} - {tuman}*\n\n🏘️ Mahallalardan birini tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif parts[0] == "MAH":
        if len(parts) < 4:
            await query.edit_message_text("❌ Nimadir xato bo'ldi.")
            return
        viloyat, tuman, mahalla = parts[1], parts[2], parts[3]
        info = DATA.get(viloyat, {}).get('tumanlar', {}).get(tuman, {}).get('mfylar', {}).get(mahalla)
        
        if not info:
            await query.edit_message_text(f"❌ {mahalla} uchun ma'lumot topilmadi.")
            return

        out = f"📍 *{viloyat} - {tuman}*\n"
        out += f"🏘️ *{mahalla}*\n\n"
        
        xodimlar = info.get('xodimlar', {})
        for lavozim, malumot in xodimlar.items():
            if malumot.get('ism'):
                lavozim_nomi = lavozim.replace('_', ' ').title()
                out += f"*{lavozim_nomi}:*\n"
                out += f"👤 {malumot['ism']}\n"
                if malumot.get('telefon'):
                    out += f"📞 {malumot['telefon']}\n"
                if malumot.get('email'):
                    out += f"📧 {malumot['email']}\n"
                out += "\n"

        out += f"\n🕐 {datetime.now().strftime('%H:%M')}"

        keyboard = [
            [InlineKeyboardButton("🔙 Mahallalar", callback_data=f"TUM|{viloyat}|{tuman}")],
            [InlineKeyboardButton("🔙 Tumanlar", callback_data=f"VIL|{viloyat}")],
            [InlineKeyboardButton("🏠 Bosh sahifa", callback_data="BACK|HOME")]
        ]
        await query.edit_message_text(out, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif parts[0] == "BACK":
        if parts[1] == "HOME":
            keyboard = []
            for v in get_viloyatlar():
                keyboard.append([InlineKeyboardButton(f"🏛️ {v}", callback_data=f"VIL|{v}")])
            await query.edit_message_text(
                "👋 *Smart Mahalla* botiga xush kelibsiz!\n\n🏛️ Viloyatingizni tanlang:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
@app.route('/admin/toggle_mahalla_status', methods=['POST'])
@login_required
def toggle_mahalla_status():
    try:
        DATA = load_data()
        viloyat_nomi = request.json.get('viloyat_nomi', '').strip()
        tuman_nomi = request.json.get('tuman_nomi', '').strip()
        mahalla_nomi = request.json.get('mahalla_nomi', '').strip()
        new_status = request.json.get('new_status', 'faol')
        
        if not all([viloyat_nomi, tuman_nomi, mahalla_nomi]):
            return jsonify({'success': False, 'message': 'Barcha maydonlar to\'ldirilmagan'})
            
        if (viloyat_nomi not in DATA or 
            tuman_nomi not in DATA[viloyat_nomi]['tumanlar'] or 
            mahalla_nomi not in DATA[viloyat_nomi]['tumanlar'][tuman_nomi]['mfylar']):
            return jsonify({'success': False, 'message': 'MFY topilmadi'})
        
        DATA[viloyat_nomi]['tumanlar'][tuman_nomi]['mfylar'][mahalla_nomi]['holat'] = new_status
        success = save_data(DATA)
        
        if success:
            status_text = "faollashtirildi" if new_status == 'faol' else "nofaollashtirildi"
            add_activity("MFY holati o'zgartirildi", 
                        f"{viloyat_nomi}, {tuman_nomi}, {mahalla_nomi} MFYsi {status_text}", 
                        session.get('username'))
            return jsonify({'success': True, 'message': f'MFY {status_text}!'})
        else:
            return jsonify({'success': False, 'message': 'Saqlashda xato'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Xato: {e}'})
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 *Smart Mahalla Bot*

*Buyruqlar:*
/start - Botni ishga tushirish
/help - Yordam
/stats - Statistika

*Maʼlumotlar:*
• Viloyat -> Tuman -> Mahalla
• MFY xodimlari va telefon raqamlari
• Foydalanuvchilar soni

📍 *Ishlatish:* Viloyat -> Tuman -> Mahalla tanlang
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    DATA = load_data()
    stats = calculate_stats(DATA)
    
    stats_text = f"""
📊 *Smart Mahallah Statistika*

🏛️ *Viloyatlar/Shaharlar:* {stats['total_regions']} ta
📍 *Tumanlar:* {stats['total_districts']} ta
🏘️ *Mahallalar:* {stats['total_neighborhoods']} ta
👨‍💼 *Xodimlar:* {stats['total_staff']} ta

🔄 *Soʻngi yangilanish:* {datetime.now().strftime("%d.%m.%Y %H:%M")}
    """
    await update.message.reply_text(stats_text, parse_mode="Markdown")

# Botni ishga tushirish
def run_bot():
    BOT_TOKEN = os.environ.get('BOT_TOKEN', "7953323094:AAE81rkkc8oAb5tp8W2dTCLJy55NRxlm_rs")
    
    try:
        # Yangi event loop yaratish
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
        app_bot.add_handler(CommandHandler("start", start))
        app_bot.add_handler(CommandHandler("help", help_command))
        app_bot.add_handler(CommandHandler("stats", stats_command))
        app_bot.add_handler(CallbackQueryHandler(button_handler))

        print("🤖 Smart Mahallah Bot ishga tushdi...")
        
        # Botni ishga tushirish
        app_bot.run_polling()
    except Exception as e:
        print(f"❌ Bot xatosi: {e}")

# Asosiy funksiya
def main():
    # Kerakli papkalarni yaratish
    for folder in ['templates', 'backups', 'exports']:
        if not os.path.exists(folder):
            os.makedirs(folder)
    
    print("🚀 Dasturni ishga tushiramiz...")
    
    # Botni alohida threadda ishga tushirish
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    print("🌐 Admin panel http://localhost:5000/admin da ishga tushdi")
    print("🔐 Login: smartmahalla, Parol: SmartMahalla1.0v")
    print("🤖 Bot ishga tushirildi")
    print("📊 Ma'lumotlar bazasi yuklandi")
    
    # Flask serverni ishga tushirish
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    main()