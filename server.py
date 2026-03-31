import os
import sqlite3
import json
import hmac
import hashlib
import bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import urllib.parse
import requests
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, redirect, session
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder=".", static_url_path="")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
CORS(app, origins=CORS_ORIGINS)

limiter = Limiter(get_remote_address, app=app, default_limits=[])

_BLOCKED_EXTENSIONS = {".py", ".db", ".env", ".sh", ".txt", ".jsonl"}
_BLOCKED_NAMES = {"Procfile", "Dockerfile", "docker-compose.yml", "requirements.txt"}

@app.before_request
def block_sensitive_files():
    path = request.path.lstrip("/")
    name = path.split("/")[-1] if path else ""
    ext = os.path.splitext(name)[1].lower()
    if ext in _BLOCKED_EXTENSIONS or name in _BLOCKED_NAMES:
        from flask import abort
        abort(404)

REVOLUT_SECRET_KEY = os.getenv("REVOLUT_SECRET_KEY", "")
REVOLUT_PUBLIC_KEY = os.getenv("REVOLUT_PUBLIC_KEY", "")
# Set REVOLUT_ENV=live in Railway when switching to production keys
REVOLUT_ENV = os.getenv("REVOLUT_ENV", "sandbox")
REVOLUT_API_BASE = (
    "https://merchant.revolut.com"
    if REVOLUT_ENV == "live"
    else "https://sandbox-merchant.revolut.com"
)
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
SHOP_PHONE = os.getenv("SHOP_PHONE", "40733768278")
SITE_URL = os.getenv("SITE_URL", "")
REVOLUT_WEBHOOK_SECRET = os.getenv("REVOLUT_WEBHOOK_SECRET", "")
# ── Stripe ─────────────────────────────────────────────────────────────────────
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "")
DASHBOARD_API_TOKEN = os.getenv("DASHBOARD_API_TOKEN", "")

_DATA_DIR = os.getenv("DATA_DIR", os.path.dirname(__file__))
PRICES_DB = os.path.join(_DATA_DIR, "prices.db")
ORDERS_DB = os.path.join(_DATA_DIR, "orders.db")

app.secret_key = os.getenv("ADMIN_SECRET_KEY", "dev-secret-change-in-prod")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

_db_initialized = False

# ── Default price seed data (matches the JS constants in index.html) ──────────
DEFAULT_PRICES = {
    "iphone": {
        "iPhone 17 Pro Max": {"Display Aftermarket":1200,"Display ORIGINAL":2000,"Acumulator":750,"Sticla Spate":900,"Difuzor / Buzzer":300,"Modul Incarcare":500,"Microfon":500,"Montaj Placa de Baza":300,"Curatare Apa (Oxid)":300,"Resoftare / Update":150},
        "iPhone 17 Pro": {"Display Aftermarket":900,"Display ORIGINAL":1800,"Acumulator":750,"Sticla Spate":800,"Difuzor / Buzzer":300,"Modul Incarcare":500,"Microfon":500,"Montaj Placa de Baza":300,"Curatare Apa (Oxid)":300,"Resoftare / Update":150},
        "iPhone 17 Air": {"Display Aftermarket":900,"Display ORIGINAL":1700,"Acumulator":600,"Sticla Spate":700,"Difuzor / Buzzer":300,"Modul Incarcare":450,"Microfon":450,"Montaj Placa de Baza":300,"Curatare Apa (Oxid)":300,"Resoftare / Update":150},
        "iPhone 17": {"Display Aftermarket":850,"Display ORIGINAL":1600,"Acumulator":550,"Sticla Spate":650,"Difuzor / Buzzer":300,"Modul Incarcare":450,"Microfon":450,"Montaj Placa de Baza":300,"Curatare Apa (Oxid)":300,"Resoftare / Update":150},
        "iPhone 16 Pro Max": {"Display Aftermarket":1100,"Display ORIGINAL":1850,"Acumulator":700,"Sticla Spate":800,"Difuzor / Buzzer":300,"Modul Incarcare":450,"Microfon":450,"Montaj Placa de Baza":300,"Curatare Apa (Oxid)":300,"Resoftare / Update":150},
        "iPhone 16 Pro": {"Display Aftermarket":800,"Display ORIGINAL":1700,"Acumulator":700,"Sticla Spate":750,"Difuzor / Buzzer":300,"Modul Incarcare":450,"Microfon":500,"Montaj Placa de Baza":300,"Curatare Apa (Oxid)":300,"Resoftare / Update":150},
        "iPhone 16 Plus": {"Display Aftermarket":800,"Display ORIGINAL":2350,"Acumulator":500,"Sticla Spate":650,"Difuzor / Buzzer":300,"Modul Incarcare":450,"Microfon":500,"Montaj Placa de Baza":300,"Curatare Apa (Oxid)":300,"Resoftare / Update":150},
        "iPhone 16": {"Display Aftermarket":800,"Display ORIGINAL":1480,"Acumulator":500,"Sticla Spate":600,"Difuzor / Buzzer":300,"Modul Incarcare":450,"Microfon":450,"Montaj Placa de Baza":300,"Curatare Apa (Oxid)":300,"Resoftare / Update":150},
        "iPhone 15 Pro Max": {"Display Aftermarket":700,"Display ORIGINAL":1450,"Sticla LCD":900,"Acumulator":550,"Sticla Spate":700,"Difuzor / Buzzer":300,"Modul Incarcare":450,"Microfon":570,"Montaj Placa de Baza":300,"Curatare Apa (Oxid)":300,"Resoftare / Update":150},
        "iPhone 15 Pro": {"Display Aftermarket":700,"Display ORIGINAL":1450,"Sticla LCD":700,"Acumulator":550,"Sticla Spate":650,"Difuzor / Buzzer":300,"Modul Incarcare":450,"Microfon":500,"Montaj Placa de Baza":300,"Curatare Apa (Oxid)":300,"Resoftare / Update":150},
        "iPhone 15 Plus": {"Display Aftermarket":490,"Display ORIGINAL":1300,"Sticla LCD":700,"Acumulator":450,"Sticla Spate":600,"Difuzor / Buzzer":300,"Modul Incarcare":450,"Microfon":500,"Montaj Placa de Baza":300,"Curatare Apa (Oxid)":300,"Resoftare / Update":150},
        "iPhone 15": {"Display Aftermarket":480,"Display ORIGINAL":1200,"Sticla LCD":550,"Acumulator":400,"Sticla Spate":600,"Difuzor / Buzzer":300,"Modul Incarcare":450,"Microfon":450,"Montaj Placa de Baza":300,"Curatare Apa (Oxid)":300,"Resoftare / Update":150},
        "iPhone 14 Pro Max": {"Display Aftermarket":650,"Display ORIGINAL":1550,"Sticla LCD":600,"Acumulator":500,"Sticla Spate":450,"Difuzor / Buzzer":300,"Modul Incarcare":450,"Microfon":500,"Montaj Placa de Baza":250,"Curatare Apa (Oxid)":250,"Resoftare / Update":150},
        "iPhone 14 Pro": {"Display Aftermarket":600,"Display ORIGINAL":1000,"Sticla LCD":550,"Acumulator":450,"Sticla Spate":450,"Difuzor / Buzzer":300,"Modul Incarcare":450,"Microfon":450,"Montaj Placa de Baza":250,"Curatare Apa (Oxid)":250,"Resoftare / Update":150},
        "iPhone 14 Plus": {"Display Aftermarket":750,"Display ORIGINAL":1000,"Sticla LCD":550,"Acumulator":430,"Sticla Spate":450,"Difuzor / Buzzer":300,"Modul Incarcare":450,"Microfon":450,"Montaj Placa de Baza":250,"Curatare Apa (Oxid)":250,"Resoftare / Update":150},
        "iPhone 14": {"Display Aftermarket":550,"Display ORIGINAL":800,"Sticla LCD":550,"Acumulator":400,"Sticla Spate":450,"Difuzor / Buzzer":300,"Modul Incarcare":450,"Microfon":450,"Montaj Placa de Baza":250,"Curatare Apa (Oxid)":250,"Resoftare / Update":150},
        "iPhone 13 Pro Max": {"Display Aftermarket":530,"Display ORIGINAL":1100,"Sticla LCD":550,"Acumulator":450,"Sticla Spate":450,"Difuzor / Buzzer":300,"Modul Incarcare":450,"Microfon":450,"Montaj Placa de Baza":250,"Curatare Apa (Oxid)":250,"Resoftare / Update":150},
        "iPhone 13 Pro": {"Display Aftermarket":480,"Display ORIGINAL":900,"Sticla LCD":500,"Acumulator":400,"Sticla Spate":450,"Difuzor / Buzzer":300,"Modul Incarcare":450,"Microfon":450,"Montaj Placa de Baza":250,"Curatare Apa (Oxid)":250,"Resoftare / Update":150},
        "iPhone 13": {"Display Aftermarket":450,"Display ORIGINAL":600,"Sticla LCD":450,"Acumulator":450,"Sticla Spate":400,"Difuzor / Buzzer":300,"Modul Incarcare":400,"Microfon":400,"Montaj Placa de Baza":250,"Curatare Apa (Oxid)":250,"Resoftare / Update":150},
        "iPhone 12 Pro Max": {"Display Aftermarket":470,"Display ORIGINAL":800,"Sticla LCD":500,"Acumulator":400,"Sticla Spate":400,"Difuzor / Buzzer":250,"Modul Incarcare":350,"Microfon":650,"Mufa Jack":650,"Camera Principala":750,"Geam Camera":300,"Flex Proxy":650,"Buton Power - Volum":300,"Montaj Placa de Baza":250,"Reconditionare Sticla Spate":490,"Carcasa Completa":940,"Curatare Apa (Oxid)":250,"Resoftare / Update":150,"Folii de Protectie":100},
        "iPhone 12 Pro": {"Display Aftermarket":380,"Display ORIGINAL":700,"Sticla LCD":500,"Acumulator":450,"Sticla Spate":400,"Difuzor / Buzzer":200,"Modul Incarcare":390,"Microfon":390,"Mufa Jack":390,"Camera Principala":700,"Geam Camera":300,"Flex Proxy":600,"Buton Power - Volum":250,"Montaj Placa de Baza":200,"Reconditionare Sticla Spate":450,"Carcasa Completa":850,"Curatare Apa (Oxid)":200,"Resoftare / Update":150,"Folii de Protectie":100},
        "iPhone 12": {"Display Aftermarket":380,"Display ORIGINAL":700,"Sticla LCD":500,"Acumulator":400,"Sticla Spate":400,"Difuzor / Buzzer":200,"Modul Incarcare":350,"Microfon":350,"Mufa Jack":350,"Camera Principala":650,"Geam Camera":300,"Flex Proxy":550,"Buton Power - Volum":250,"Montaj Placa de Baza":200,"Reconditionare Sticla Spate":400,"Carcasa Completa":650,"Curatare Apa (Oxid)":200,"Resoftare / Update":150,"Folii de Protectie":100},
        "iPhone 12 mini": {"Display Aftermarket":450,"Display ORIGINAL":650,"Sticla LCD":400,"Acumulator":250,"Sticla Spate":400,"Difuzor / Buzzer":150,"Modul Incarcare":330,"Microfon":330,"Mufa Jack":330,"Camera Principala":600,"Geam Camera":250,"Flex Proxy":450,"Buton Power - Volum":300,"Montaj Placa de Baza":200,"Reconditionare Sticla Spate":370,"Carcasa Completa":1000,"Curatare Apa (Oxid)":200,"Resoftare / Update":150,"Folii de Protectie":100},
        "iPhone 11 Pro Max": {"Display Aftermarket":370,"Display ORIGINAL":650,"Sticla LCD":400,"Acumulator":260,"Sticla Spate":380,"Difuzor / Buzzer":150,"Modul Incarcare":350,"Microfon":350,"Mufa Jack":350,"Geam Camera":220,"Flex Proxy":520,"Buton Power - Volum":150,"Montaj Placa de Baza":200,"Reconditionare Sticla Spate":400,"Carcasa Completa":750,"Curatare Apa (Oxid)":200,"Resoftare / Update":150,"Folii de Protectie":100},
        "iPhone 11 Pro": {"Display Aftermarket":350,"Display ORIGINAL":500,"Sticla LCD":400,"Acumulator":250,"Sticla Spate":380,"Difuzor / Buzzer":250,"Modul Incarcare":300,"Microfon":300,"Mufa Jack":300,"Camera Principala":550,"Geam Camera":180,"Flex Proxy":490,"Buton Power - Volum":150,"Montaj Placa de Baza":200,"Reconditionare Sticla Spate":320,"Carcasa Completa":700,"Curatare Apa (Oxid)":180,"Resoftare / Update":150,"Folii de Protectie":100},
        "iPhone 11": {"Display Aftermarket":350,"Display ORIGINAL":500,"Sticla LCD":400,"Acumulator":250,"Sticla Spate":380,"Difuzor / Buzzer":390,"Modul Incarcare":250,"Microfon":250,"Mufa Jack":250,"Camera Principala":550,"Geam Camera":170,"Flex Proxy":450,"Buton Power - Volum":290,"Montaj Placa de Baza":200,"Reconditionare Sticla Spate":450,"Carcasa Completa":400,"Curatare Apa (Oxid)":145,"Resoftare / Update":150,"Folii de Protectie":100},
        "iPhone Xs Max": {"Display Aftermarket":350,"Display ORIGINAL":600,"Sticla LCD":400,"Acumulator":220,"Sticla Spate":300,"Difuzor / Buzzer":200,"Modul Incarcare":200,"Microfon":250,"Mufa Jack":250,"Camera Principala":450,"Geam Camera":140,"Flex Proxy":270,"Buton Power - Volum":140,"Montaj Placa de Baza":150,"Reconditionare Sticla Spate":300,"Carcasa Completa":400,"Curatare Apa (Oxid)":145,"Resoftare / Update":130,"Folii de Protectie":100},
        "iPhone XS": {"Display Aftermarket":300,"Display ORIGINAL":450,"Sticla LCD":350,"Acumulator":230,"Sticla Spate":300,"Difuzor / Buzzer":170,"Modul Incarcare":250,"Microfon":250,"Mufa Jack":250,"Camera Principala":450,"Geam Camera":160,"Flex Proxy":250,"Buton Power - Volum":140,"Montaj Placa de Baza":150,"Reconditionare Sticla Spate":350,"Carcasa Completa":400,"Curatare Apa (Oxid)":145,"Resoftare / Update":110,"Folii de Protectie":100},
        "iPhone XR": {"Display Aftermarket":330,"Display ORIGINAL":450,"Sticla LCD":350,"Acumulator":200,"Sticla Spate":300,"Difuzor / Buzzer":180,"Modul Incarcare":230,"Microfon":230,"Mufa Jack":230,"Camera Principala":350,"Geam Camera":140,"Flex Proxy":250,"Buton Power - Volum":120,"Montaj Placa de Baza":150,"Reconditionare Sticla Spate":260,"Carcasa Completa":360,"Curatare Apa (Oxid)":145,"Resoftare / Update":120,"Folii de Protectie":100},
        "iPhone X": {"Display Aftermarket":300,"Display ORIGINAL":450,"Sticla LCD":350,"Acumulator":230,"Sticla Spate":300,"Difuzor / Buzzer":140,"Modul Incarcare":210,"Microfon":210,"Mufa Jack":210,"Camera Principala":350,"Geam Camera":140,"Flex Proxy":220,"Buton Power - Volum":140,"Montaj Placa de Baza":150,"Reconditionare Sticla Spate":280,"Carcasa Completa":400,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Folii de Protectie":80},
    },
    "samsung": {
        "Samsung S25 Ultra": {"Display":1850,"Acumulator":480,"Casca / Sita":250,"Difuzor / Buzzer":350,"Modul/Mufa Incarcare":400,"Microfon":400,"Geam Camera":150,"Montaj Placa de Baza":150,"Inlocuire Capac":450,"Curatare Apa (Oxid)":150,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S25 Plus": {"Display":980,"Acumulator":400,"Casca / Sita":250,"Difuzor / Buzzer":350,"Modul/Mufa Incarcare":370,"Microfon":370,"Geam Camera":150,"Montaj Placa de Baza":150,"Inlocuire Capac":450,"Curatare Apa (Oxid)":150,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S25": {"Display":950,"Acumulator":400,"Casca / Sita":250,"Difuzor / Buzzer":350,"Modul/Mufa Incarcare":350,"Microfon":350,"Geam Camera":150,"Montaj Placa de Baza":150,"Inlocuire Capac":450,"Curatare Apa (Oxid)":150,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S24 Ultra": {"Display":1550,"Sticla":700,"Acumulator":320,"Casca / Sita":250,"Difuzor / Buzzer":350,"Modul/Mufa Incarcare":350,"Microfon":350,"Geam Camera":150,"Montaj Placa de Baza":150,"Inlocuire Capac":450,"Curatare Apa (Oxid)":150,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S24 Plus": {"Display":1100,"Sticla":600,"Acumulator":320,"Casca / Sita":250,"Difuzor / Buzzer":350,"Modul/Mufa Incarcare":350,"Microfon":350,"Geam Camera":150,"Montaj Placa de Baza":150,"Inlocuire Capac":450,"Curatare Apa (Oxid)":150,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S24": {"Display":800,"Sticla":600,"Acumulator":340,"Casca / Sita":250,"Difuzor / Buzzer":350,"Modul/Mufa Incarcare":350,"Microfon":350,"Geam Camera":150,"Montaj Placa de Baza":150,"Inlocuire Capac":450,"Curatare Apa (Oxid)":150,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S23 Ultra": {"Display":1400,"Sticla":700,"Acumulator":320,"Casca / Sita":250,"Difuzor / Buzzer":350,"Modul/Mufa Incarcare":350,"Microfon":350,"Geam Camera":150,"Montaj Placa de Baza":150,"Inlocuire Capac":450,"Curatare Apa (Oxid)":150,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S23 Plus": {"Display":800,"Sticla":600,"Acumulator":340,"Casca / Sita":250,"Difuzor / Buzzer":350,"Modul/Mufa Incarcare":340,"Microfon":340,"Geam Camera":150,"Montaj Placa de Baza":150,"Inlocuire Capac":450,"Curatare Apa (Oxid)":150,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S23": {"Display":750,"Sticla":600,"Acumulator":340,"Casca / Sita":250,"Difuzor / Buzzer":350,"Modul/Mufa Incarcare":340,"Microfon":340,"Geam Camera":150,"Montaj Placa de Baza":150,"Inlocuire Capac":450,"Curatare Apa (Oxid)":150,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S22 Ultra": {"Display":1250,"Sticla":650,"Acumulator":340,"Casca / Sita":250,"Difuzor / Buzzer":350,"Modul/Mufa Incarcare":280,"Microfon":280,"Geam Camera":150,"Montaj Placa de Baza":150,"Inlocuire Capac":450,"Curatare Apa (Oxid)":150,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S22 Plus": {"Display":800,"Sticla":550,"Acumulator":350,"Casca / Sita":250,"Difuzor / Buzzer":350,"Modul/Mufa Incarcare":280,"Microfon":280,"Geam Camera":150,"Montaj Placa de Baza":150,"Inlocuire Capac":450,"Curatare Apa (Oxid)":150,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S22": {"Display":800,"Sticla":550,"Acumulator":340,"Casca / Sita":250,"Difuzor / Buzzer":350,"Modul/Mufa Incarcare":280,"Microfon":280,"Geam Camera":150,"Montaj Placa de Baza":150,"Inlocuire Capac":450,"Curatare Apa (Oxid)":150,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S21 Ultra / 5g": {"Display":1200,"Sticla":700,"Acumulator":350,"Casca / Sita":180,"Difuzor / Buzzer":350,"Modul/Mufa Incarcare":350,"Microfon":350,"Mufa Jack":350,"Camera Principala":550,"Geam Camera":150,"Camera Selfie":350,"Buton Power - Volum":300,"Montaj Placa de Baza":200,"Inlocuire Capac":450,"Curatare Apa (Oxid)":150,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S21 Plus": {"Display":950,"Sticla":550,"Acumulator":310,"Casca / Sita":180,"Difuzor / Buzzer":220,"Modul/Mufa Incarcare":250,"Microfon":250,"Mufa Jack":250,"Camera Principala":520,"Geam Camera":150,"Camera Selfie":300,"Buton Power - Volum":300,"Montaj Placa de Baza":200,"Inlocuire Capac":450,"Curatare Apa (Oxid)":150,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S21": {"Display":650,"Sticla":550,"Acumulator":310,"Casca / Sita":180,"Difuzor / Buzzer":200,"Modul/Mufa Incarcare":250,"Microfon":250,"Mufa Jack":250,"Camera Principala":350,"Geam Camera":170,"Camera Selfie":250,"Buton Power - Volum":250,"Montaj Placa de Baza":200,"Inlocuire Capac":390,"Curatare Apa (Oxid)":150,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S20 FE": {"Sticla":550,"Acumulator":250,"Casca / Sita":180,"Difuzor / Buzzer":200,"Modul/Mufa Incarcare":220,"Microfon":220,"Mufa Jack":220,"Camera Principala":280,"Geam Camera":170,"Camera Selfie":250,"Buton Power - Volum":250,"Montaj Placa de Baza":150,"Inlocuire Capac":350,"Curatare Apa (Oxid)":150,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S20": {"Display":850,"Sticla":650,"Acumulator":250,"Casca / Sita":180,"Difuzor / Buzzer":290,"Modul/Mufa Incarcare":250,"Microfon":250,"Mufa Jack":250,"Camera Principala":410,"Geam Camera":170,"Camera Selfie":190,"Buton Power - Volum":290,"Montaj Placa de Baza":150,"Inlocuire Capac":290,"Curatare Apa (Oxid)":145,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S20 Plus": {"Display":1100,"Sticla":750,"Acumulator":250,"Casca / Sita":180,"Difuzor / Buzzer":270,"Modul/Mufa Incarcare":250,"Microfon":250,"Mufa Jack":250,"Camera Principala":420,"Geam Camera":170,"Camera Selfie":210,"Buton Power - Volum":220,"Montaj Placa de Baza":100,"Inlocuire Capac":390,"Curatare Apa (Oxid)":145,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S20 Ultra / 5g": {"Display":1100,"Sticla":750,"Acumulator":250,"Casca / Sita":180,"Difuzor / Buzzer":350,"Modul/Mufa Incarcare":350,"Microfon":350,"Mufa Jack":350,"Camera Principala":510,"Geam Camera":190,"Camera Selfie":290,"Buton Power - Volum":220,"Montaj Placa de Baza":100,"Inlocuire Capac":390,"Curatare Apa (Oxid)":145,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S10 Plus": {"Display":1250,"Sticla":650,"Acumulator":250,"Casca / Sita":180,"Difuzor / Buzzer":220,"Modul/Mufa Incarcare":220,"Microfon":220,"Mufa Jack":220,"Camera Principala":320,"Geam Camera":140,"Camera Selfie":190,"Buton Power - Volum":200,"Montaj Placa de Baza":100,"Inlocuire Capac":350,"Curatare Apa (Oxid)":145,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S10": {"Display":1150,"Sticla":650,"Acumulator":250,"Casca / Sita":180,"Difuzor / Buzzer":199,"Modul/Mufa Incarcare":210,"Microfon":210,"Mufa Jack":210,"Camera Principala":280,"Geam Camera":140,"Camera Selfie":180,"Buton Power - Volum":190,"Montaj Placa de Baza":100,"Inlocuire Capac":290,"Curatare Apa (Oxid)":145,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung S10 Lite / E": {"Display":850,"Sticla":400,"Acumulator":250,"Casca / Sita":180,"Difuzor / Buzzer":180,"Modul/Mufa Incarcare":190,"Microfon":190,"Mufa Jack":190,"Camera Principala":260,"Geam Camera":140,"Camera Selfie":170,"Buton Power - Volum":180,"Montaj Placa de Baza":100,"Inlocuire Capac":290,"Curatare Apa (Oxid)":145,"Resoftare / Update":150,"Salvare Date":150},
        "Samsung A10": {"Display":265,"Sticla":320,"Acumulator":180,"Casca / Sita":130,"Difuzor / Buzzer":150,"Modul/Mufa Incarcare":140,"Microfon":140,"Mufa Jack":140,"Geam Camera":80},
        "Samsung A20": {"Display":350,"Sticla":320,"Acumulator":180,"Casca / Sita":130,"Difuzor / Buzzer":150,"Modul/Mufa Incarcare":140,"Microfon":140,"Mufa Jack":140,"Geam Camera":80},
        "Samsung A30": {"Display":450,"Sticla":320,"Acumulator":180,"Casca / Sita":130,"Difuzor / Buzzer":150,"Modul/Mufa Incarcare":230,"Microfon":230,"Mufa Jack":230,"Geam Camera":80},
        "Samsung A40": {"Display":490,"Sticla":320,"Acumulator":180,"Casca / Sita":130,"Difuzor / Buzzer":150,"Modul/Mufa Incarcare":230,"Microfon":230,"Mufa Jack":230,"Geam Camera":120},
        "Samsung A50": {"Display":345,"Sticla":320,"Acumulator":180,"Casca / Sita":130,"Difuzor / Buzzer":150,"Modul/Mufa Incarcare":230,"Microfon":230,"Mufa Jack":230,"Geam Camera":120},
        "Samsung A51": {"Display":480,"Sticla":320,"Acumulator":170,"Casca / Sita":180,"Difuzor / Buzzer":180,"Modul/Mufa Incarcare":250,"Microfon":250,"Mufa Jack":250,"Camera Principala":210,"Geam Camera":140,"Camera Selfie":180,"Buton Power - Volum":180,"Montaj Placa de Baza":100,"Inlocuire Capac":180,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung A52": {"Display":510,"Sticla":320,"Acumulator":160,"Casca / Sita":180,"Difuzor / Buzzer":180,"Modul/Mufa Incarcare":180,"Microfon":180,"Mufa Jack":180,"Camera Principala":180,"Geam Camera":150,"Camera Selfie":150,"Buton Power - Volum":150,"Montaj Placa de Baza":100,"Inlocuire Capac":180,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung A53 5G": {"Display":530,"Sticla":320,"Acumulator":180,"Casca / Sita":180,"Difuzor / Buzzer":180,"Modul/Mufa Incarcare":220,"Microfon":220,"Mufa Jack":220,"Camera Principala":170,"Geam Camera":120,"Camera Selfie":150,"Buton Power - Volum":150,"Montaj Placa de Baza":100,"Inlocuire Capac":150,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung A54 5G": {"Display":530,"Sticla":320,"Acumulator":220,"Casca / Sita":180,"Difuzor / Buzzer":180,"Modul/Mufa Incarcare":220,"Microfon":220,"Mufa Jack":220,"Camera Principala":160,"Geam Camera":90,"Camera Selfie":140,"Buton Power - Volum":150,"Montaj Placa de Baza":100,"Inlocuire Capac":170,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung A55 5G": {"Display":540,"Sticla":320,"Acumulator":220,"Casca / Sita":180,"Difuzor / Buzzer":180,"Modul/Mufa Incarcare":220,"Microfon":220,"Mufa Jack":220,"Camera Principala":160,"Geam Camera":90,"Camera Selfie":170,"Buton Power - Volum":190,"Montaj Placa de Baza":100,"Inlocuire Capac":170,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung A35 5G": {"Display":520,"Sticla":320,"Acumulator":220,"Casca / Sita":180,"Difuzor / Buzzer":180,"Modul/Mufa Incarcare":220,"Microfon":220,"Mufa Jack":220,"Camera Principala":180,"Geam Camera":90,"Camera Selfie":150,"Buton Power - Volum":190,"Montaj Placa de Baza":100,"Inlocuire Capac":170,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung A34 5G": {"Display":530,"Sticla":320,"Acumulator":220,"Casca / Sita":180,"Difuzor / Buzzer":180,"Modul/Mufa Incarcare":220,"Microfon":220,"Mufa Jack":220,"Camera Principala":150,"Geam Camera":90,"Camera Selfie":140,"Buton Power - Volum":130,"Montaj Placa de Baza":100,"Inlocuire Capac":150,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung A33 5G": {"Display":480,"Sticla":320,"Acumulator":170,"Casca / Sita":180,"Difuzor / Buzzer":180,"Modul/Mufa Incarcare":140,"Microfon":140,"Mufa Jack":140,"Camera Principala":180,"Geam Camera":120,"Camera Selfie":150,"Buton Power - Volum":150,"Montaj Placa de Baza":100,"Inlocuire Capac":150,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung A25 5G": {"Display":500,"Sticla":320,"Acumulator":220,"Casca / Sita":180,"Difuzor / Buzzer":180,"Modul/Mufa Incarcare":220,"Microfon":220,"Mufa Jack":220,"Camera Principala":190,"Geam Camera":90,"Camera Selfie":160,"Buton Power - Volum":190,"Montaj Placa de Baza":100,"Inlocuire Capac":170,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung A24": {"Display":530,"Sticla":320,"Acumulator":150,"Casca / Sita":180,"Difuzor / Buzzer":180,"Modul/Mufa Incarcare":200,"Microfon":200,"Mufa Jack":200,"Camera Principala":170,"Geam Camera":120,"Camera Selfie":140,"Buton Power - Volum":150,"Montaj Placa de Baza":100,"Inlocuire Capac":150,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung A23": {"Display":350,"Sticla":320,"Acumulator":180,"Casca / Sita":180,"Difuzor / Buzzer":180,"Modul/Mufa Incarcare":150,"Microfon":150,"Mufa Jack":150,"Camera Principala":180,"Geam Camera":120,"Camera Selfie":150,"Buton Power - Volum":150,"Montaj Placa de Baza":100,"Inlocuire Capac":180,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung A14": {"Display":310,"Sticla":320,"Acumulator":150,"Casca / Sita":180,"Difuzor / Buzzer":180,"Modul/Mufa Incarcare":200,"Microfon":200,"Mufa Jack":200,"Camera Principala":170,"Geam Camera":120,"Camera Selfie":140,"Buton Power - Volum":150,"Montaj Placa de Baza":100,"Inlocuire Capac":150,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung A13": {"Display":310,"Sticla":320,"Acumulator":150,"Casca / Sita":180,"Difuzor / Buzzer":180,"Modul/Mufa Incarcare":180,"Microfon":180,"Mufa Jack":180,"Camera Principala":170,"Geam Camera":150,"Camera Selfie":150,"Buton Power - Volum":150,"Montaj Placa de Baza":100,"Inlocuire Capac":180,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung A12": {"Display":300,"Sticla":320,"Acumulator":140,"Casca / Sita":180,"Difuzor / Buzzer":180,"Modul/Mufa Incarcare":180,"Microfon":180,"Mufa Jack":180,"Camera Principala":190,"Geam Camera":130,"Camera Selfie":170,"Buton Power - Volum":180,"Montaj Placa de Baza":100,"Inlocuire Capac":180,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung Note 20 Ultra 5G": {"Display":1550,"Sticla":750,"Acumulator":250,"Casca / Sita":180,"Difuzor / Buzzer":210,"Modul/Mufa Incarcare":250,"Microfon":250,"Mufa Jack":250,"Camera Principala":390,"Geam Camera":150,"Camera Selfie":230,"Buton Power - Volum":250,"Montaj Placa de Baza":100,"Inlocuire Capac":390,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung Note 20": {"Display":1150,"Sticla":600,"Acumulator":250,"Casca / Sita":180,"Difuzor / Buzzer":210,"Modul/Mufa Incarcare":250,"Microfon":250,"Mufa Jack":250,"Camera Principala":350,"Geam Camera":150,"Camera Selfie":200,"Buton Power - Volum":220,"Montaj Placa de Baza":100,"Inlocuire Capac":350,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung Note 10 Plus": {"Display":1650,"Sticla":690,"Acumulator":260,"Casca / Sita":140,"Difuzor / Buzzer":220,"Modul/Mufa Incarcare":220,"Microfon":220,"Mufa Jack":220,"Camera Principala":250,"Geam Camera":130,"Camera Selfie":210,"Buton Power - Volum":200,"Montaj Placa de Baza":100,"Inlocuire Capac":320,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung Note 10": {"Display":1150,"Sticla":650,"Acumulator":260,"Difuzor / Buzzer":180,"Modul/Mufa Incarcare":210,"Microfon":210,"Mufa Jack":210,"Camera Principala":220,"Geam Camera":110,"Camera Selfie":190,"Buton Power - Volum":190,"Montaj Placa de Baza":100,"Inlocuire Capac":290,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung Note 9": {"Display":950,"Sticla":590,"Acumulator":240,"Casca / Sita":130,"Difuzor / Buzzer":170,"Modul/Mufa Incarcare":190,"Microfon":190,"Mufa Jack":190,"Camera Principala":190,"Geam Camera":90,"Camera Selfie":180,"Buton Power - Volum":160,"Montaj Placa de Baza":100,"Inlocuire Capac":250,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung Note 8": {"Display":1050,"Sticla":550,"Acumulator":180,"Casca / Sita":120,"Difuzor / Buzzer":150,"Modul/Mufa Incarcare":160,"Microfon":160,"Mufa Jack":160,"Camera Principala":150,"Geam Camera":90,"Camera Selfie":140,"Buton Power - Volum":150,"Montaj Placa de Baza":100,"Inlocuire Capac":170,"Curatare Apa (Oxid)":145,"Resoftare / Update":100,"Salvare Date":100},
        "Samsung Z Fold 7": {"Display":2200,"Sticla":950,"Acumulator":350,"Casca / Sita":180,"Difuzor / Buzzer":210,"Modul/Mufa Incarcare":250,"Microfon":250,"Mufa Jack":250},
        "Samsung Z Fold 6": {"Display":2000,"Sticla":900,"Acumulator":350,"Casca / Sita":180,"Difuzor / Buzzer":210,"Modul/Mufa Incarcare":250,"Microfon":250,"Mufa Jack":250},
        "Samsung Z Fold 5": {"Display":1900,"Sticla":850,"Acumulator":300,"Casca / Sita":180,"Difuzor / Buzzer":210,"Modul/Mufa Incarcare":250,"Microfon":250,"Mufa Jack":250},
        "Samsung Z Fold 4": {"Display":1800,"Sticla":800,"Acumulator":300,"Casca / Sita":180,"Difuzor / Buzzer":210,"Modul/Mufa Incarcare":250,"Microfon":250,"Mufa Jack":250},
        "Samsung Z Fold 3": {"Display":1550,"Sticla":750,"Acumulator":250,"Casca / Sita":180,"Difuzor / Buzzer":210,"Modul/Mufa Incarcare":250,"Microfon":250,"Mufa Jack":250},
        "Samsung Z Flip 7": {"Display":1200,"Sticla":500,"Acumulator":200,"Casca / Sita":150,"Difuzor / Buzzer":180,"Modul/Mufa Incarcare":200,"Microfon":200,"Mufa Jack":200},
        "Samsung Z Flip 6": {"Display":1100,"Sticla":480,"Acumulator":200,"Casca / Sita":150,"Difuzor / Buzzer":180,"Modul/Mufa Incarcare":200,"Microfon":200,"Mufa Jack":200},
        "Samsung Z Flip 5": {"Display":1000,"Sticla":450,"Acumulator":180,"Casca / Sita":150,"Difuzor / Buzzer":170,"Modul/Mufa Incarcare":190,"Microfon":190,"Mufa Jack":190},
        "Samsung Z Flip 4": {"Display":950,"Sticla":420,"Acumulator":180,"Casca / Sita":150,"Difuzor / Buzzer":170,"Modul/Mufa Incarcare":190,"Microfon":190,"Mufa Jack":190},
        "Samsung Z Flip 3": {"Display":900,"Sticla":400,"Acumulator":160,"Casca / Sita":150,"Difuzor / Buzzer":160,"Modul/Mufa Incarcare":180,"Microfon":180,"Mufa Jack":180},
    },
}

_S0 = {"Display":0,"Acumulator":0,"Casca / Sita":0,"Difuzor / Buzzer":0,"Modul/Mufa Incarcare":0,"Microfon":0,"Geam Camera":0,"Montaj Placa de Baza":0,"Inlocuire Capac":0,"Curatare Apa (Oxid)":0,"Resoftare / Update":0,"Salvare Date":0}

DEFAULT_PRICES.update({
    "huawei": {m: dict(_S0) for m in ["P30","P30 Pro","Nova 5T","Mate 30","Mate 30 Pro","P40","P40 Lite","P40 Pro","P40 Pro+","Mate 40","Mate 40 Pro","P50","P50 Pro","Nova 9","Nova 10","Nova 10 Pro","Mate 50","Mate 50 Pro","Pura 70","Pura 70 Pro","Pura 70 Ultra"]},
    "honor":  {m: dict(_S0) for m in ["Honor 90","Honor 90 Pro","Honor Magic 5 Pro","Honor Magic 6 Pro","Honor Magic 7 Pro","Honor 200","Honor 200 Pro","Honor X8b","Honor X9b","Honor X9c"]},
    "xiaomi": {m: dict(_S0) for m in ["Mi 10","Mi 10 Pro","Mi 10T","Mi 10T Pro","Mi 10 Lite","Mi 11","Mi 11 Pro","Mi 11 Ultra","Mi 11 Lite 5G","Xiaomi 12","Xiaomi 12 Pro","Xiaomi 12T","Xiaomi 12T Pro","Xiaomi 12 Lite","Xiaomi 13","Xiaomi 13 Pro","Xiaomi 13T","Xiaomi 13T Pro","Xiaomi 13 Lite","Xiaomi 14","Xiaomi 14 Pro","Xiaomi 14T","Xiaomi 14T Pro","Xiaomi 15","Xiaomi 15 Pro"]},
    "oppo":   {m: dict(_S0) for m in ["Reno 4","Reno 4 Pro","Reno 5","Reno 5 Pro","Reno 6","Reno 6 Pro","Reno 7","Reno 7 Pro","Reno 8","Reno 8 Pro","Reno 10","Reno 10 Pro","Reno 12","Reno 12 Pro","Reno 13","Reno 13 Pro","Find X2","Find X2 Pro","Find X3","Find X3 Pro","Find X5","Find X5 Pro","Find X6","Find X6 Pro","Find X7","Find X7 Ultra"]},
    "motorola": {m: dict(_S0) for m in ["Moto G9 Play","Moto G9 Plus","Moto G9 Power","Moto G30","Moto G50","Moto G60","Moto G72","Moto G82 5G","Moto G14","Moto G24","Moto G34 5G","Moto G54 5G","Moto G64 5G","Moto G84 5G","Moto G85 5G","Moto Edge 20","Moto Edge 20 Pro","Moto Edge 30","Moto Edge 30 Pro","Moto Edge 30 Neo","Moto Edge 30 Ultra","Moto Edge 40","Moto Edge 40 Pro","Moto Edge 40 Neo","Moto Edge 50","Moto Edge 50 Pro","Moto Edge 50 Ultra","Moto Edge 50 Fusion"]},
    "oneplus": {m: dict(_S0) for m in ["OnePlus 8","OnePlus 8 Pro","OnePlus 8T","OnePlus 9","OnePlus 9 Pro","OnePlus 9R","OnePlus 10 Pro","OnePlus 10T","OnePlus 11","OnePlus 11R","OnePlus 12","OnePlus 12R","OnePlus 13","OnePlus 13R","Nord","Nord 2","Nord 2T","Nord 3","Nord 4","Nord CE","Nord CE 2","Nord CE 3","Nord CE 4"]},
    "realme": {m: dict(_S0) for m in ["Realme 8","Realme 8 Pro","Realme 8i","Realme 9","Realme 9 Pro","Realme 9 Pro+","Realme 9i","Realme 10","Realme 10 Pro","Realme 10 Pro+","Realme 11","Realme 11 Pro","Realme 11 Pro+","Realme 12","Realme 12 Pro","Realme 12 Pro+","Realme GT","Realme GT 2","Realme GT 2 Pro","Realme GT Neo 2","Realme GT Neo 3","Realme GT Neo 5","Realme GT 6","Realme C31","Realme C33","Realme C35","Realme C51","Realme C53","Realme C55","Realme C67"]},
    "google": {m: dict(_S0) for m in ["Pixel 6","Pixel 6 Pro","Pixel 6a","Pixel 7","Pixel 7 Pro","Pixel 7a","Pixel 8","Pixel 8 Pro","Pixel 8a","Pixel 9","Pixel 9 Pro","Pixel 9 Pro XL","Pixel 9 Pro Fold","Pixel Fold"]},
})


def get_db():
    conn = sqlite3.connect(PRICES_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def get_next_order_number():
    conn = get_orders_db()
    conn.execute("CREATE TABLE IF NOT EXISTS order_counter (id INTEGER PRIMARY KEY AUTOINCREMENT)")
    cursor = conn.execute("INSERT INTO order_counter DEFAULT VALUES")
    number = cursor.lastrowid
    conn.commit()
    conn.close()
    return number


def get_orders_db():
    conn = sqlite3.connect(ORDERS_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_orders_db():
    conn = get_orders_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id           TEXT PRIMARY KEY,
            services     TEXT NOT NULL,
            date         TEXT NOT NULL,
            time_slot    TEXT NOT NULL,
            amount       REAL NOT NULL,
            status       TEXT DEFAULT 'in_lucru',
            notes        TEXT DEFAULT '',
            customer_phone TEXT DEFAULT '',
            customer_name  TEXT,
            brand        TEXT,
            model        TEXT,
            created_at   TEXT NOT NULL,
            completed_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pending_orders (
            order_id         TEXT PRIMARY KEY,
            revolut_order_id TEXT,
            order_data       TEXT NOT NULL,
            created_at       TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_order(order_id, services, date, time_slot, amount, phone, name, brand, model):
    conn = get_orders_db()
    conn.execute(
        """INSERT OR IGNORE INTO orders
           (id, services, date, time_slot, amount, customer_phone, customer_name, brand, model, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (order_id, json.dumps(services), date, time_slot, amount, phone, name, brand, model,
         datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def push_to_dashboard(order_id, services, date, time_slot, amount, phone, name, brand, model, description=""):
    """Fire-and-forget POST to dashboard API. Silently fails if dashboard is not configured."""
    if not DASHBOARD_URL or not DASHBOARD_API_TOKEN:
        return
    try:
        resp = requests.post(
            f"{DASHBOARD_URL}/api/orders",
            json={
                "order_id":      order_id,
                "services":      services,
                "date":          date,
                "timeSlot":      time_slot,
                "amount":        amount,
                "customer_phone": phone,
                "customer_name": name,
                "brand":         brand,
                "model":         model,
                "description":   description,
            },
            headers={"X-Auth-Token": DASHBOARD_API_TOKEN},
            timeout=5,
        )
        print(f"[Dashboard] Push {order_id} → {resp.status_code}")
    except Exception as e:
        print(f"[Dashboard] Push failed for {order_id}: {e}")


def confirm_order(order_id, services, date, time_slot, amount, phone, name, brand, model):
    """Save order to DB and remove from pending. Used by both webhook and return-URL handlers."""
    save_order(order_id, services, date, time_slot, amount, phone, name, brand, model)
    conn = get_orders_db()
    conn.execute("DELETE FROM pending_orders WHERE order_id = ?", (order_id,))
    conn.commit()
    conn.close()
    push_to_dashboard(order_id, services, date, time_slot, amount, phone, name, brand, model)


def init_prices_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            brand   TEXT NOT NULL,
            model   TEXT NOT NULL,
            service TEXT NOT NULL,
            price   INTEGER NOT NULL,
            PRIMARY KEY (brand, model, service)
        )
    """)
    for brand, models in DEFAULT_PRICES.items():
        for model, services in models.items():
            for service, price in services.items():
                conn.execute(
                    "INSERT OR IGNORE INTO prices VALUES (?, ?, ?, ?)",
                    (brand, model, service, price),
                )
    conn.commit()
    print(f"[Prices DB] Seeded missing entries")
    conn.close()


@app.before_request
def ensure_db():
    global _db_initialized
    if not _db_initialized:
        init_prices_db()
        init_orders_db()
        _db_initialized = True


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/config")
def get_config():
    """Return public config the frontend needs."""
    return jsonify({
        "revolut_public_key": REVOLUT_PUBLIC_KEY,
        "revolut_embed_url": f"{REVOLUT_API_BASE}/embed.js",
        "shop_phone": SHOP_PHONE,
    })


@app.route("/api/prices", methods=["GET"])
def get_prices():
    """Return all service prices from the database."""
    conn = get_db()
    rows = conn.execute("SELECT brand, model, service, price FROM prices").fetchall()
    conn.close()
    result = {}
    for row in rows:
        brand, model, service, price = row["brand"], row["model"], row["service"], row["price"]
        if brand not in result:
            result[brand] = {}
        if model not in result[brand]:
            result[brand][model] = {}
        result[brand][model][service] = price
    resp = jsonify(result)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp



@app.route("/api/order-status/<order_id>")
def order_status(order_id):
    conn = get_orders_db()
    row = conn.execute("SELECT id FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row:
        conn.close()
        return jsonify({"status": "completed", "order_id": row["id"]})
    pending = conn.execute("SELECT * FROM pending_orders WHERE order_id = ?", (order_id,)).fetchone()
    conn.close()
    if pending:
        return jsonify({"status": "pending"})
    return jsonify({"status": "not_found"})


@app.route("/api/create-order", methods=["POST"])
def create_order():
    data = request.json
    amount = data.get("amount", 0)
    currency = data.get("currency", "RON")
    services = data.get("services", [])
    date = data.get("date", "")
    time_slot = data.get("timeSlot", "")
    phone = data.get("phone", "")
    name = data.get("name", "")
    model = data.get("model") or ""
    brand = data.get("brand", "")
    description = data.get("description", "")

    order_id = f"GSM-{get_next_order_number()}"

    # Build redirect URL for card payments
    app_base = os.getenv("APP_URL", SITE_URL or request.host_url).rstrip("/")
    return_url = f"{app_base}/payment-return?order_id={order_id}"
    print(f"[Return URL] {return_url}")

    # Save pending order so /payment-return can retrieve it
    pending_data = json.dumps({
        "services": services, "date": date, "time_slot": time_slot,
        "amount": amount, "phone": phone, "name": name,
        "model": model, "brand": brand, "description": description,
    })
    conn = get_orders_db()
    conn.execute(
        "INSERT OR IGNORE INTO pending_orders (order_id, revolut_order_id, order_data, created_at) VALUES (?, ?, ?, ?)",
        (order_id, "", pending_data, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

    if amount == 0:
        # Free order — skip Revolut, confirm immediately
        confirm_order(order_id, services, date, time_slot, amount, phone, name, brand, model)
        print(f"[Orders DB] Free order {order_id} confirmed directly")
        return jsonify({"order_id": order_id, "revolut_order_token": None, "mode": "free"})

    if REVOLUT_SECRET_KEY:
        try:
            resp = requests.post(
                f"{REVOLUT_API_BASE}/api/1.0/orders",
                headers={
                    "Authorization": f"Bearer {REVOLUT_SECRET_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "amount": int(amount * 100),
                    "currency": currency,
                    "description": f"GSM Service — {order_id}",
                    "redirect_url": return_url,
                    "merchant_order_ext_ref": order_id,
                },
                timeout=10,
            )
            if not resp.ok:
                print(f"[Revolut ERROR] {resp.status_code}: {resp.text}")
            resp.raise_for_status()
            revolut_data = resp.json()
            print(f"[Revolut OK] Response: {revolut_data}")
            token = revolut_data.get("token") or revolut_data.get("public_id")
            revolut_order_id = revolut_data.get("id", "")

            conn = get_orders_db()
            conn.execute(
                "UPDATE pending_orders SET revolut_order_id = ? WHERE order_id = ?",
                (revolut_order_id, order_id)
            )
            conn.commit()
            conn.close()

            if not token:
                print(f"[Revolut ERROR] No token/public_id in response: {revolut_data}")
                return jsonify({"error": "Revolut did not return a payment token"}), 502
            return jsonify({
                "order_id": order_id,
                "revolut_order_id": revolut_order_id,
                "revolut_order_token": token,
                "revolut_checkout_url": revolut_data.get("checkout_url", ""),
                "mode": "live",
            })
        except Exception as e:
            print(f"[Revolut ERROR] {e}")
            return jsonify({"error": f"Payment provider error: {e}"}), 502
    else:
        print(f"[MOCK] Created order {order_id}: {amount} {currency}")
        return jsonify({
            "order_id": order_id,
            "revolut_order_token": None,
            "mode": "mock",
        })


@app.route("/payment-return")
def payment_return():
    base = SITE_URL.rstrip("/") if SITE_URL else ""
    order_id = request.args.get("order_id", "")
    if not order_id:
        return redirect(f"{base}/?payment_error=1")

    conn = get_orders_db()
    row = conn.execute(
        "SELECT * FROM pending_orders WHERE order_id = ?", (order_id,)
    ).fetchone()
    conn.close()

    if not row:
        # Order may have already been processed by the webhook — check orders table
        conn2 = get_orders_db()
        existing = conn2.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        conn2.close()
        if existing:
            params = urllib.parse.urlencode({
                "confirmed": "1",
                "order_id": existing["id"],
                "name": existing["customer_name"] or "",
                "model": existing["model"] or "",
                "amount": existing["amount"],
                "date": existing["date"],
                "time": existing["time_slot"],
            })
            app_base = os.getenv("APP_URL", SITE_URL or request.host_url).rstrip("/")
            return redirect(f"{app_base}/payment-done?{params}")
        return redirect(f"{base}/?payment_error=not_found")

    revolut_order_id = row["revolut_order_id"]
    order_data = json.loads(row["order_data"])

    # Verify payment with Revolut (skip in mock mode)
    if REVOLUT_SECRET_KEY and revolut_order_id:
        try:
            resp = requests.get(
                f"{REVOLUT_API_BASE}/api/1.0/orders/{revolut_order_id}",
                headers={"Authorization": f"Bearer {REVOLUT_SECRET_KEY}"},
                timeout=10,
            )
            resp.raise_for_status()
            revolut_order = resp.json()
            state = revolut_order.get("state", "")
            print(f"[Revolut] Order {revolut_order_id} state: {state}")
            if state not in ("COMPLETED", "AUTHORISED"):
                return redirect(f"{base}/?payment_error=not_completed")
        except Exception as e:
            print(f"[Revolut Verify ERROR] {e}")
            return redirect(f"{base}/?payment_error=verify_failed")
    else:
        print(f"[Mock] Skipping Revolut verification for {order_id}")

    # Extract order data
    services = order_data["services"]
    date = order_data["date"]
    time_slot = order_data["time_slot"]
    amount = order_data["amount"]
    phone = order_data["phone"]
    name = order_data["name"]
    model = order_data.get("model") or ""
    brand = order_data["brand"]

    confirm_order(order_id, services, date, time_slot, amount, phone, name, brand, model)
    print(f"[Orders DB] Saved and confirmed order {order_id}")

    # Redirect to payment-done page (auto-closes tab, posts message to opener)
    params = urllib.parse.urlencode({
        "confirmed": "1",
        "order_id": order_id,
        "name": name,
        "model": model,
        "amount": amount,
        "date": date,
        "time": time_slot,
    })
    app_base = os.getenv("APP_URL", SITE_URL or request.host_url).rstrip("/")
    return redirect(f"{app_base}/payment-done?{params}")


@app.route("/payment-done")
def payment_done():
    """Served in the Revolut tab after payment. Posts message to opener and closes itself."""
    data = {k: request.args.get(k, "") for k in request.args}
    data["action"] = "paymentDone"
    msg_json = json.dumps(data).replace("<", r"\u003c").replace(">", r"\u003e").replace("&", r"\u0026")
    fallback = (SITE_URL.rstrip("/") if SITE_URL else "") + "/?" + request.query_string.decode("utf-8")
    html = f"""<!DOCTYPE html><html>
<head><meta charset="utf-8"><title>Plata confirmata</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body{{margin:0;display:flex;align-items:center;justify-content:center;min-height:100vh;background:#0d0c12;font-family:sans-serif;color:#F4EDFF}}
  .box{{text-align:center;padding:40px 32px}}
  .check{{width:64px;height:64px;background:#22c55e;border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 20px}}
  h2{{font-size:1.2rem;margin:0 0 8px}}
  p{{color:#9ca3af;font-size:.9rem;margin:0 0 24px}}
  button{{background:#8176FF;color:#fff;border:none;border-radius:12px;padding:14px 32px;font-size:.95rem;font-weight:600;cursor:pointer}}
</style>
</head><body>
<div class="box">
  <div class="check"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div>
  <h2>Plata efectuata cu succes!</h2>
  <p>Poti inchide aceasta fereastra.</p>
  <button onclick="tryClose()">Inchide fereastra</button>
</div>
<script>
(function(){{
  var msg = {msg_json};
  function tryClose() {{
    if (window.opener && !window.opener.closed) {{
      window.opener.postMessage(msg, "{SITE_URL.rstrip('/') if SITE_URL else '*'}");
    }}
    try {{ window.open('','_self',''); window.close(); }} catch(e) {{}}
  }}
  tryClose();
  setTimeout(tryClose, 500);
  if (!window.opener || window.opener.closed) {{
    setTimeout(function() {{ window.location.href = "{SITE_URL.rstrip('/') if SITE_URL else '/'}"; }}, 3000);
  }}
}})();
</script>
</body></html>"""
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/api/revolut-webhook", methods=["POST"])
def revolut_webhook():
    payload = request.get_data()

    # Signature verification is mandatory — reject if secret not configured
    if not REVOLUT_WEBHOOK_SECRET:
        print(f"[Webhook] REVOLUT_WEBHOOK_SECRET not set — rejecting all webhooks")
        return jsonify({"error": "Webhook not configured"}), 401

    sig_header = request.headers.get("Revolut-Signature", "")
    timestamp = request.headers.get("Revolut-Request-Timestamp", "")
    signed_payload = f"v1.{timestamp}.{payload.decode('utf-8')}"
    expected_sig = hmac.new(
        REVOLUT_WEBHOOK_SECRET.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(sig_header, f"v1={expected_sig}"):
        print(f"[Webhook] Signature mismatch — rejecting")
        return jsonify({"error": "Invalid signature"}), 401

    data = request.json or {}
    event = data.get("event", "")
    # Revolut sends our order ID in merchant_order_ext_ref (if we set it on create)
    order_id = data.get("merchant_order_ext_ref", "") or ""
    revolut_order_id = data.get("order_id", "")
    print(f"[Webhook] Event: {event}, GSM order: {order_id}, Revolut order: {revolut_order_id}")

    if event not in ("ORDER_COMPLETED", "ORDER_AUTHORISED"):
        return jsonify({"ok": True}), 200

    # Apple Pay / Google Pay can create a child Revolut order without merchant_order_ext_ref.
    # Fall back to fetching the full order from the Revolut API to recover it.
    if not order_id and revolut_order_id and REVOLUT_SECRET_KEY:
        try:
            r = requests.get(
                f"{REVOLUT_API_BASE}/api/1.0/orders/{revolut_order_id}",
                headers={"Authorization": f"Bearer {REVOLUT_SECRET_KEY}"},
                timeout=10,
            )
            if r.ok:
                order_id = r.json().get("merchant_order_ext_ref", "") or ""
                print(f"[Webhook] Recovered GSM order from Revolut API: {order_id}")
        except Exception as e:
            print(f"[Webhook] Revolut API fallback error: {e}")

    # Look up pending order (by GSM order_id if available, else by revolut_order_id)
    conn = get_orders_db()
    if order_id:
        row = conn.execute(
            "SELECT * FROM pending_orders WHERE order_id = ?", (order_id,)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM pending_orders WHERE revolut_order_id = ?", (revolut_order_id,)
        ).fetchone()
    conn.close()

    if not row:
        print(f"[Webhook] Order not in pending (may already be processed via redirect) — skipping")
        return jsonify({"ok": True}), 200

    order_id = row["order_id"]
    order_data = json.loads(row["order_data"])
    services = order_data["services"]
    date = order_data["date"]
    time_slot = order_data["time_slot"]
    amount = order_data["amount"]
    phone = order_data["phone"]
    name = order_data["name"]
    model = order_data.get("model") or ""
    brand = order_data["brand"]

    confirm_order(order_id, services, date, time_slot, amount, phone, name, brand, model)
    print(f"[Webhook] Order {order_id} confirmed and saved")

    return jsonify({"ok": True}), 200


@app.route("/api/payment-complete", methods=["POST"])
def payment_complete():
    data = request.json
    order_id = data.get("order_id", "")
    if not order_id:
        return jsonify({"error": "order_id required"}), 400

    conn = get_orders_db()
    row = conn.execute("SELECT * FROM pending_orders WHERE order_id = ?", (order_id,)).fetchone()
    conn.close()

    if not row:
        # Already processed (webhook beat us here) — return success
        conn2 = get_orders_db()
        existing = conn2.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        conn2.close()
        if existing:
            return jsonify({"success": True, "order_id": order_id})
        return jsonify({"error": "order not found"}), 404

    revolut_order_id = row["revolut_order_id"]
    order_data = json.loads(row["order_data"])

    if REVOLUT_SECRET_KEY and revolut_order_id:
        try:
            resp = requests.get(
                f"{REVOLUT_API_BASE}/api/1.0/orders/{revolut_order_id}",
                headers={"Authorization": f"Bearer {REVOLUT_SECRET_KEY}"},
                timeout=10,
            )
            resp.raise_for_status()
            state = resp.json().get("state", "")
            print(f"[payment-complete] Revolut order {revolut_order_id} state: {state}")
            if state not in ("COMPLETED", "AUTHORISED"):
                return jsonify({"error": "payment not completed"}), 402
        except Exception as e:
            print(f"[payment-complete] Revolut verify error: {e}")
            return jsonify({"error": "payment verification failed"}), 502
    else:
        print(f"[payment-complete] Mock mode — skipping Revolut verification for {order_id}")

    services  = order_data["services"]
    date      = order_data["date"]
    time_slot = order_data["time_slot"]
    amount    = order_data["amount"]
    phone     = order_data["phone"]
    name      = order_data["name"]
    model     = order_data.get("model") or ""
    brand     = order_data["brand"]

    confirm_order(order_id, services, date, time_slot, amount, phone, name, brand, model)
    print(f"[Orders DB] Saved order {order_id}")

    return jsonify({"success": True, "order_id": order_id})




@app.route("/api/notify-order", methods=["POST"])
def notify_order():
    data = request.json or {}
    order_id = data.get("order_id", "")
    services = data.get("services", [])
    date = data.get("date", "")
    time_slot = data.get("timeSlot", "")
    amount = data.get("amount", 0)
    phone = data.get("phone", "")
    name = data.get("name", "")
    model = data.get("model") or ""
    description = data.get("description", "")
    is_free = amount == 0

    service_list = "\n".join(
        f"  • {s['name']}" + (f" — {s['price']} lei" if s.get('price') else " — GRATUIT")
        for s in services
    )
    try:
        date_display = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        date_display = date

    message = (
        f"{'Diagnosticare Noua' if is_free else 'Programare Noua'} — {order_id}\n\n"
        f"Client: {name}\n"
        f"Telefon: {phone}\n"
        f"Dispozitiv de reparat: {model}\n"
        f"Data: {date_display}\n"
        f"Ora: {time_slot}\n\n"
        f"Servicii:\n{service_list}"
        + (f"\n\nProblema descrisa:\n  {description}" if description else "")
    )

    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": message},
                timeout=10,
            )
            print(f"[Notify] Telegram sent for {order_id}")
        except Exception as e:
            print(f"[Notify Telegram ERROR] {e}")

    if WHATSAPP_TOKEN and WHATSAPP_PHONE_ID:
        try:
            requests.post(
                f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_ID}/messages",
                headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"},
                json={"messaging_product": "whatsapp", "to": SHOP_PHONE, "type": "text", "text": {"body": message}},
                timeout=10,
            )
            print(f"[Notify] WhatsApp sent for {order_id}")
        except Exception as e:
            print(f"[Notify WhatsApp ERROR] {e}")

    print(f"\n{'='*50}\n{message}\n{'='*50}\n")

    # Save free/diagnoza appointments to orders DB and push to dashboard
    brand = data.get("brand", "alte dispozitive")
    save_order(order_id, services, date, time_slot, amount, phone, name, brand, model)
    push_to_dashboard(order_id, services, date, time_slot, amount, phone, name, brand, model, description)

    return jsonify({"ok": True})


# ── Admin ─────────────────────────────────────────────────────────────────────

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect("/admin/login")
        return f(*args, **kwargs)
    return decorated


@app.route("/admin/login", methods=["GET", "POST"])
@limiter.limit("3 per minute; 10 per hour", methods=["POST"])
def admin_login():
    if request.method == "POST":
        user = request.form.get("username", "")
        pw = request.form.get("password", "")
        user_ok = (not ADMIN_USERNAME) or hmac.compare_digest(user, ADMIN_USERNAME)
        pass_ok = False
        if ADMIN_PASSWORD and pw:
            stored = ADMIN_PASSWORD.encode()
            if stored.startswith(b"$2b$") or stored.startswith(b"$2a$"):
                pass_ok = bcrypt.checkpw(pw.encode(), stored)
            else:
                pass_ok = hmac.compare_digest(pw, ADMIN_PASSWORD)
        if user_ok and pass_ok:
            session["admin_logged_in"] = True
            return redirect("/admin")
        return send_from_directory(".", "admin.html"), 401
    return send_from_directory(".", "admin.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect("/admin/login")


@app.route("/admin")
@admin_required
def admin_page():
    return send_from_directory(".", "admin.html")


@app.route("/api/admin/prices", methods=["GET"])
@admin_required
def admin_get_prices():
    conn = get_db()
    rows = conn.execute(
        "SELECT brand, model, service, price FROM prices ORDER BY brand, model, service"
    ).fetchall()
    conn.close()
    return jsonify([{"brand": r[0], "model": r[1], "service": r[2], "price": r[3]} for r in rows])


@app.route("/api/admin/price", methods=["POST"])
@admin_required
def admin_upsert_price():
    data = request.get_json()
    brand   = data.get("brand", "").strip()
    model   = data.get("model", "").strip()
    service = data.get("service", "").strip()
    price   = data.get("price")
    if not brand or not model or not service or price is None:
        return jsonify({"error": "brand, model, service, price required"}), 400
    try:
        price = int(price)
    except (ValueError, TypeError):
        return jsonify({"error": "price must be integer"}), 400
    conn = get_db()
    conn.execute(
        "INSERT INTO prices (brand, model, service, price) VALUES (?,?,?,?) "
        "ON CONFLICT(brand, model, service) DO UPDATE SET price=excluded.price",
        (brand, model, service, price),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/admin/price", methods=["DELETE"])
@admin_required
def admin_delete_price():
    data = request.get_json()
    brand   = data.get("brand", "").strip()
    model   = data.get("model", "").strip()
    service = data.get("service", "").strip()
    if not brand or not model or not service:
        return jsonify({"error": "brand, model, service required"}), 400
    conn = get_db()
    conn.execute("DELETE FROM prices WHERE brand=? AND model=? AND service=?", (brand, model, service))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/admin/service/add", methods=["POST"])
@admin_required
def admin_add_service():
    """Add a new service column for all models of a brand (price = 0)."""
    data = request.get_json()
    brand   = (data.get("brand") or "").strip()
    service = (data.get("service") or "").strip()
    if not brand or not service:
        return jsonify({"error": "brand and service required"}), 400
    conn = get_db()
    models = [r[0] for r in conn.execute(
        "SELECT DISTINCT model FROM prices WHERE brand=?", (brand,)
    ).fetchall()]
    for model in models:
        conn.execute(
            "INSERT OR IGNORE INTO prices (brand, model, service, price) VALUES (?,?,?,0)",
            (brand, model, service),
        )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "models_updated": len(models)})


@app.route("/api/admin/service/remove", methods=["POST"])
@admin_required
def admin_remove_service():
    """Remove an entire service column for a brand."""
    data = request.get_json()
    brand   = (data.get("brand") or "").strip()
    service = (data.get("service") or "").strip()
    if not brand or not service:
        return jsonify({"error": "brand and service required"}), 400
    conn = get_db()
    conn.execute("DELETE FROM prices WHERE brand=? AND service=?", (brand, service))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/admin/bulk-import", methods=["POST"])
@admin_required
def admin_bulk_import():
    """Import prices from JSON array: [{brand, model, service, price}]"""
    rows = request.get_json()
    if not isinstance(rows, list):
        return jsonify({"error": "expected array"}), 400
    conn = get_db()
    count = 0
    for r in rows:
        try:
            conn.execute(
                "INSERT INTO prices (brand, model, service, price) VALUES (?,?,?,?) "
                "ON CONFLICT(brand, model, service) DO UPDATE SET price=excluded.price",
                (r["brand"].strip(), r["model"].strip(), r["service"].strip(), int(r["price"])),
            )
            count += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "imported": count})


if __name__ == "__main__":
    init_prices_db()
    init_orders_db()
    print("\n  GSM Service Backend")
    print(f"  Revolut: {'configured' if REVOLUT_SECRET_KEY else 'MOCK mode'}")
    print(f"  WhatsApp: {'configured' if WHATSAPP_TOKEN else 'not configured'}")
    print(f"  Telegram: {'configured' if TELEGRAM_BOT_TOKEN else 'not configured'}")
    print(f"  Shop phone: {SHOP_PHONE}")
    print(f"\n  Open http://localhost:8080")
    print(f"  Admin mode: http://localhost:8080/?admin=1\n")
    port = int(os.getenv("PORT", 8080))
    app.run(debug=False, host="0.0.0.0", port=port)
