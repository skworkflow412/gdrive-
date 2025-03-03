from flask import Flask, request, jsonify, render_template
import requests, re, os
from pymongo import MongoClient
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from celery import Celery
import redis

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default_secret_key")

# MongoDB Connection
client = MongoClient(os.getenv("MONGO_URI", "mongodb://mongodb:27017/"))
db = client["upload_database"]
uploads_collection = db["uploads"]

# Redis & Celery Config
redis_instance = redis.Redis(host="redis", port=6379, db=0)
celery = Celery(app.name, broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"))
celery.conf.update(result_backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0"))

# API Keys
STREAMTAPE_API_KEY = os.getenv("STREAMTAPE_API_KEY")
FILEPRESS_API_KEY = os.getenv("FILEPRESS_API_KEY")

# Rate Limiting
limiter = Limiter(app, key_func=get_remote_address)
login_manager = LoginManager()
login_manager.init_app(app)

users = {"admin": "password123"}

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(username):
    return User(username) if username in users else None

def extract_gdrive_id(gdrive_link):
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', gdrive_link)
    return match.group(1) if match else None

def get_gdrive_direct_link(file_id):
    return f"https://drive.google.com/uc?export=download&id={file_id}"

@celery.task
def process_upload(gdrive_link):
    file_id = extract_gdrive_id(gdrive_link)
    direct_link = get_gdrive_direct_link(file_id)

    streamtape_link = upload_to_streamtape(direct_link)
    filepress_link = upload_to_filepress(direct_link)

    uploads_collection.insert_one({
        "gdrive_link": gdrive_link,
        "streamtape_link": streamtape_link,
        "filepress_link": filepress_link
    })
    
    return {"StreamTape": streamtape_link, "FilePress": filepress_link}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    if username in users and users[username] == password:
        login_user(User(username))
        return jsonify({"message": "Login successful!"})
    return jsonify({"error": "Invalid credentials!"})

@app.route("/upload", methods=["POST"])
@login_required
@limiter.limit("5 per minute")
def upload():
    data = request.json
    gdrive_link = data.get("gdrive_link")
    task = process_upload.apply_async(args=[gdrive_link])
    return jsonify({"task_id": task.id, "status": "Processing"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
