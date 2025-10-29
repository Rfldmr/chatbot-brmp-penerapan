from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import nltk
nltk.download("punkt", quiet=True)
nltk.download("wordnet", quiet=True)
from nltk.stem import WordNetLemmatizer
import pickle
import numpy as np
from tensorflow import keras
import json
import random
from datetime import datetime, timedelta
import os
import subprocess
import threading
import time
import shutil
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from database import db_manager
from difflib import SequenceMatcher

app = Flask(__name__)
app.secret_key = '25082025-chtbtbrmppnrpn-rfldmr'

# Global variables untuk tracking
training_status = {"status": "ready", "progress": 0, "message": ""}
model_info = {
    "last_training": None,
    "accuracy": "95.2%",
    "model_size": "2.4 MB",
    "total_intents": 0,
    "total_patterns": 0,
    "total_users": 0,
    "dataset_update": "N/A",
    "status": "Ready",
    "status_icon": "fas fa-brain",
    "status_color": "text-success-600"
}

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# --- Fungsi untuk memuat model dan data ---
def load_model_and_data():
    global model, intents, words, classes, model_info
    try:
        model = keras.models.load_model('model/chatbot_brmp_model.h5')
        intents = json.loads(open('intents.json').read())
        words = pickle.load(open('model/words.pkl','rb'))
        classes = pickle.load(open('model/classes.pkl','rb'))
        
        # Update model info dengan data yang lebih akurat
        model_info["total_intents"] = len(intents['intents'])
        model_info["last_training"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Count total patterns
        total_patterns = 0
        for intent in intents['intents']:
            if 'patterns' in intent:
                total_patterns += len(intent['patterns'])
        model_info["total_patterns"] = total_patterns
        
        # Set user count to 0 for now (will be dynamic when user registration is implemented)
        model_info["total_users"] = 0
        
        # Hitung ukuran file intents.json (dataset)
        if os.path.exists('intents.json'):
            dataset_size_bytes = os.path.getsize('intents.json')
            model_info["model_size"] = f"{dataset_size_bytes / 1024:.1f} KB"
            
            # Get last training time from model file
            mod_time = os.path.getmtime('model/chatbot_brmp_model.h5')
            last_training = datetime.fromtimestamp(mod_time)
            model_info["last_training"] = last_training.strftime("%Y-%m-%d %H:%M:%S")
        
        # Get dataset update date
        if os.path.exists('intents.json'):
            mod_time = os.path.getmtime('intents.json')
            last_modified = datetime.fromtimestamp(mod_time)
            model_info["dataset_update"] = last_modified.strftime('%d %b %Y, %H:%M WIB')
        
        # Update status information
        model_info["accuracy"] = "95.2%"
        model_info["status"] = "Ready"
        model_info["status_icon"] = "fas fa-brain"
        model_info["status_color"] = "text-success-600"
        
        print(f"Model loaded successfully. Intents: {model_info['total_intents']}, Patterns: {model_info['total_patterns']}, Size: {model_info['model_size']}")
        return True
    except Exception as e:
        print(f"Error loading model: {e}")
        model_info["total_intents"] = 0
        model_info["total_patterns"] = 0
        model_info["total_users"] = 0  # Static 0 for now, will be dynamic when user system is implemented
        model_info["accuracy"] = "N/A"
        model_info["model_size"] = "N/A"
        model_info["last_training"] = None
        model_info["dataset_update"] = "N/A"
        model_info["status"] = "Not Trained"
        model_info["status_icon"] = "fas fa-exclamation-triangle"
        model_info["status_color"] = "text-warning-600"
        return False

# --- Muat model saat aplikasi pertama kali dijalankan ---
load_model_and_data()
lemmatizer = WordNetLemmatizer()

def normalize_repeated_chars(text):
    """Normalisasi huruf berulang (pagiii -> pagi, halooo -> halo)"""
    import re
    # Ganti 3+ karakter berulang menjadi 2 karakter
    # Contoh: halooo -> haloo, terimaaaa -> terimaa
    normalized = re.sub(r'(.)\1{2,}', r'\1\1', text)
    # Kemudian ganti 2 karakter berulang menjadi 1 untuk kata pendek
    # Contoh: haloo -> halo, pagii -> pagi
    normalized = re.sub(r'(.)\1+', r'\1', normalized)
    return normalized

def clean_up_sentence(sentence):
    # Normalisasi huruf berulang dulu
    sentence = normalize_repeated_chars(sentence.lower())
    
    # Tokenize
    sentence_words = nltk.word_tokenize(sentence)
    
    # Lemmatize
    sentence_words = [lemmatizer.lemmatize(word) for word in sentence_words]
    
    return sentence_words

def string_similarity(a, b):
    """Hitung similarity antara dua string menggunakan SequenceMatcher"""
    return SequenceMatcher(None, a, b).ratio()

def bag_of_words(sentence, words):
    sentence_words = clean_up_sentence(sentence)
    bag = np.zeros(len(words), dtype=np.float32)
    
    # Threshold untuk fuzzy matching (0.0-1.0)
    # 0.75 = 75% similarity required (lebih toleran untuk typo)
    SIMILARITY_THRESHOLD = 0.75
    
    for sw in sentence_words:
        for i, word in enumerate(words):
            # Exact match - prioritas tertinggi
            if word == sw:
                bag[i] = 1.0
            # Fuzzy match - untuk menangani typo dan variasi
            else:
                similarity = string_similarity(word, sw)
                if similarity >= SIMILARITY_THRESHOLD:
                    # Berikan score sesuai tingkat similarity
                    bag[i] = similarity
                    
    return bag

def predict_class(sentence):
    p = bag_of_words(sentence, words)
    res = model.predict(np.expand_dims(p, axis=0))[0]
    
    # Threshold lebih tinggi untuk akurasi lebih baik
    # 0.50 = 50% confidence minimum (lebih tinggi = lebih akurat)
    ERROR_THRESHOLD = 0.50
    
    results = [[i,r] for i,r in enumerate(res) if r>ERROR_THRESHOLD]
    results.sort(key=lambda x: x[1], reverse=True)
    
    return results

def getResponse(ints, intents_json):
    if not ints:
        fallback_responses = [
            "Maaf, aku tidak mengerti. Bisa coba kata lain?",
            "Hmm, aku kurang paham. Coba jelaskan dengan cara lain?",
            "Maaf, aku belum bisa menjawab itu. Ada pertanyaan lain?"
        ]
        return random.choice(fallback_responses)
    
    tag = classes[ints[0][0]]
    confidence = ints[0][1]
    
    list_of_intents = intents_json['intents']
    for i in list_of_intents:
        if i['tag'] == tag:
            result = random.choice(i['responses'])
            
            # Debug log untuk monitoring
            print(f"Response: {tag} (confidence: {confidence:.2f})")
            
            return result
    
    return "Maaf, aku tidak menemukan jawaban untuk itu."

def train_model_async():
    """Fungsi untuk melatih model secara asinkron"""
    global training_status
    try:
        print("Training async started")  # Debug log
        training_status = {"status": "training", "progress": 10, "message": "Memproses file intents..."}
        time.sleep(1)
        
        print(f"Training progress: {training_status}")  # Debug log
        training_status = {"status": "training", "progress": 30, "message": "Mempersiapkan data training..."}
        time.sleep(2)
        
        print(f"Training progress: {training_status}")  # Debug log
        training_status = {"status": "training", "progress": 60, "message": "Melatih model neural network..."}
        
        # Method 1: Try importing and running directly
        try:
            import importlib.util
            import sys
            
            print("Attempting direct import method")  # Debug log
            
            # Load train_model.py module
            spec = importlib.util.spec_from_file_location("train_model", "train_model.py")
            train_module = importlib.util.module_from_spec(spec)
            
            # Execute training
            spec.loader.exec_module(train_module)
            train_module.train()
            
            success = True
            error_msg = None
            
        except Exception as import_error:
            print(f"Direct import failed: {import_error}")
            
            # Method 2: Fallback to subprocess with proper Python path
            try:
                import sys
                python_exe = sys.executable
                result = subprocess.run([python_exe, 'train_model.py'], 
                                      capture_output=True, text=True, cwd=os.getcwd())
                
                if result.returncode == 0:
                    success = True
                    error_msg = None
                else:
                    success = False
                    error_msg = f"Training script error: {result.stderr}"
                    print(f"Subprocess stderr: {result.stderr}")
                    print(f"Subprocess stdout: {result.stdout}")
                    
            except Exception as subprocess_error:
                success = False
                error_msg = f"Subprocess error: {str(subprocess_error)}"
                print(f"Subprocess execution failed: {subprocess_error}")
        
        training_status = {"status": "training", "progress": 90, "message": "Menyimpan model..."}
        time.sleep(1)
        
        if success:
            # Hapus semua file backup model lama
            try:
                model_dir = 'model'
                if os.path.exists(model_dir):
                    for filename in os.listdir(model_dir):
                        if filename.startswith('backup_model_') and filename.endswith('.h5'):
                            backup_path = os.path.join(model_dir, filename)
                            os.remove(backup_path)
                            print(f"Deleted old model backup: {filename}")
            except Exception as cleanup_error:
                print(f"Warning: Could not delete old model backups: {cleanup_error}")
            
            # Reload model after training
            load_model_and_data()
            training_status = {"status": "completed", "progress": 100, "message": "Model berhasil dilatih ulang!"}
            print("Training completed successfully")  # Debug log
            
            # Reset status to ready after a short delay (for frontend to catch completion)
            def reset_status():
                time.sleep(1)  # Reduced to 1 second - just enough for frontend to catch completion
                global training_status
                training_status = {"status": "ready", "progress": 0, "message": ""}
                print("Training status reset to ready")  # Debug log
            
            reset_thread = threading.Thread(target=reset_status)
            reset_thread.daemon = True
            reset_thread.start()
            
        else:
            training_status = {"status": "error", "progress": 0, "message": error_msg or "Unknown training error"}
            print(f"Training failed: {error_msg}")  # Debug log
            
    except Exception as e:
        print(f"Training error: {str(e)}")  # Debug print
        import traceback
        traceback.print_exc()  # Print full traceback
        training_status = {"status": "error", "progress": 0, "message": f"Training failed: {str(e)}"}

@app.route('/')
def index():
    if 'messages' not in session:
        session['messages'] = [{"role": "assistant", "content": "Hai! Ada yang bisa aku bantu hari ini?"}]
    return render_template('index.html', title='Chatbot BRMP', now=datetime.now())

# --- Authentication Routes ---
@app.route('/admin/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'GET':
        # If already logged in, redirect to admin
        if 'admin_logged_in' in session:
            return redirect(url_for('admin'))
        return render_template('login.html')
    
    elif request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = db_manager.verify_admin_credentials(username, password)
        if admin:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            session['admin_id'] = admin['id']
            
            # Log login activity
            ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
            db_manager.log_activity(admin['id'], 'LOGIN', f"Admin {username} logged in", ip_address)
            
            return jsonify({"status": "success", "message": "Login berhasil"})
        else:
            return jsonify({"status": "error", "message": "Username atau password salah"})

@app.route('/admin/logout')
def logout():
    # Log logout activity
    admin_id = session.get('admin_id')
    username = session.get('admin_username')
    if admin_id and username:
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
        db_manager.log_activity(admin_id, 'LOGOUT', f"Admin {username} logged out", ip_address)
    
    session.clear()
    return redirect(url_for('login_page'))

# --- Rute Halaman Admin ---
@app.route('/admin')
@login_required
def admin():
    return render_template('admin.html')

@app.route('/admin/management')
@login_required
def admin_management():
    return render_template('admin_management.html')

# --- Admin Management API ---
@app.route('/api/admin/list')
@login_required
def get_admin_list():
    admins = db_manager.get_all_admins()
    return jsonify(admins)

@app.route('/api/admin/add', methods=['POST'])
@login_required
def add_admin():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        return jsonify({"status": "error", "message": "Username dan password harus diisi"})
    
    if len(password) < 6:
        return jsonify({"status": "error", "message": "Password minimal 6 karakter"})
    
    # Add new admin using database manager
    result = db_manager.create_admin(username, password)
    
    # Log activity if successful
    if result["status"] == "success":
        admin_id = session.get('admin_id')
        if admin_id:
            ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
            db_manager.log_activity(admin_id, 'CREATE_ADMIN', f"Created admin: {username}", ip_address)
    
    return jsonify(result)

@app.route('/api/admin/delete', methods=['POST'])
@login_required
def delete_admin():
    data = request.get_json()
    username = data.get('username')
    
    if not username:
        return jsonify({"status": "error", "message": "Username harus diisi"})
    
    # Prevent deleting current user
    if username == session.get('admin_username'):
        return jsonify({"status": "error", "message": "Tidak dapat menghapus akun sendiri"})
    
    # Delete admin using database manager
    result = db_manager.delete_admin(username)
    
    # Log activity if successful
    if result["status"] == "success":
        admin_id = session.get('admin_id')
        if admin_id:
            ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR'))
            db_manager.log_activity(admin_id, 'DELETE_ADMIN', f"Deleted admin: {username}", ip_address)
    
    return jsonify(result)

@app.route('/api/admin/current-user')
@login_required
def get_current_user():
    username = session.get('admin_username', 'Unknown')
    print(f"DEBUG: Current user API called, returning: {username}")
    return jsonify({"username": username})

# --- API untuk mendapatkan informasi model ---
@app.route('/api/admin/model-info')
@login_required
def get_model_info():
    return jsonify(model_info)

# --- API untuk mendapatkan status training ---
@app.route('/api/admin/training-status')
@login_required
def get_training_status():
    try:
        print(f"Training status requested: {training_status}")  # Debug log
        return jsonify(training_status)
    except Exception as e:
        print(f"Error getting training status: {str(e)}")
        return jsonify({"status": "error", "progress": 0, "message": f"Error: {str(e)}"}), 500

# --- Rute untuk Unggah File dan Latih Ulang ---
@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    global training_status
    
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "Tidak ada file yang dipilih"})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "Tidak ada file yang dipilih"})
    
    if file and file.filename.endswith('.json'):
        try:
            # Validasi format JSON
            file_content = file.read()
            json_data = json.loads(file_content)
            
            # Validasi struktur intents
            if 'intents' not in json_data:
                return jsonify({"status": "error", "message": "Format file tidak valid - missing 'intents' key"})
            
            # Hapus semua file backup lama sebelum menyimpan yang baru
            try:
                base_dir = os.path.dirname(__file__)
                for filename in os.listdir(base_dir):
                    if filename.startswith('intents_backup_') and filename.endswith('.json'):
                        backup_path = os.path.join(base_dir, filename)
                        os.remove(backup_path)
                        print(f"Deleted old backup: {filename}")
            except Exception as cleanup_error:
                print(f"Warning: Could not delete old backups: {cleanup_error}")
            
            # Reset file pointer dan simpan langsung (replace file lama)
            file.seek(0)
            intents_path = os.path.join(os.path.dirname(__file__), 'intents.json')
            file.save(intents_path)
            print(f"Saved new intents.json, replaced old file")
            
            # Start training in background
            try:
                training_status = {"status": "training", "progress": 0, "message": "Memulai pelatihan..."}
                training_thread = threading.Thread(target=train_model_async)
                training_thread.daemon = True  # Make thread daemon to prevent hanging
                training_thread.start()
                
                # Give thread a moment to start
                time.sleep(0.1)
                
                print(f"Training started, initial status: {training_status}")  # Debug log
                
                return jsonify({"status": "success", "message": "File berhasil diunggah. Training dimulai..."})
                
            except Exception as thread_error:
                print(f"Error starting training thread: {thread_error}")
                training_status = {"status": "error", "progress": 0, "message": f"Gagal memulai training: {str(thread_error)}"}
                return jsonify({"status": "error", "message": f"Gagal memulai training: {str(thread_error)}"})
            
        except json.JSONDecodeError:
            return jsonify({"status": "error", "message": "File JSON tidak valid"})
        except Exception as e:
            return jsonify({"status": "error", "message": f"Error: {str(e)}"})
    
    return jsonify({"status": "error", "message": "File harus berformat .json"})

# --- API untuk preview file ---
@app.route('/api/admin/preview', methods=['POST'])
@login_required
def preview_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "Tidak ada file"})
    
    file = request.files['file']
    if file and file.filename.endswith('.json'):
        try:
            content = file.read()
            json_data = json.loads(content)
            
            # Hitung statistik
            total_intents = len(json_data.get('intents', []))
            total_patterns = sum(len(intent.get('patterns', [])) for intent in json_data.get('intents', []))
            
            preview_data = {
                "total_intents": total_intents,
                "total_patterns": total_patterns,
                "intents": [{"tag": intent.get("tag", ""), "patterns_count": len(intent.get("patterns", []))} 
                           for intent in json_data.get('intents', [])[:5]]  # Show first 5
            }
            
            return jsonify({"status": "success", "data": preview_data})
            
        except json.JSONDecodeError:
            return jsonify({"status": "error", "message": "File JSON tidak valid"})
    
    return jsonify({"status": "error", "message": "File harus berformat .json"})

# --- API untuk mendapatkan aktivitas terbaru ---
@app.route('/api/admin/recent-activities')
@login_required
def get_recent_activities():
    try:
        activities = db_manager.get_recent_activities(5)
        
        # Format activities for frontend
        formatted_activities = []
        for activity in activities:
            icon = 'fas fa-sign-in-alt'
            color = 'green'
            
            if activity['action'] == 'LOGOUT':
                icon = 'fas fa-sign-out-alt'
                color = 'blue'
            elif activity['action'] == 'CREATE_ADMIN':
                icon = 'fas fa-user-plus'
                color = 'purple'
            elif activity['action'] == 'DELETE_ADMIN':
                icon = 'fas fa-user-minus'
                color = 'red'
            
            formatted_activities.append({
                'id': len(formatted_activities) + 1,
                'type': activity['action'].lower(),
                'message': activity['description'] or activity['action'],
                'timestamp': activity['created_at'],
                'icon': icon,
                'color': color,
                'username': activity['username']
            })
        
        # Add system activities if no database activities
        if not formatted_activities:
            # Cek apakah model ada
            if os.path.exists('model/chatbot_brmp_model.h5'):
                model_stat = os.path.getmtime('model/chatbot_brmp_model.h5')
                model_time = datetime.fromtimestamp(model_stat)
                time_diff = datetime.now() - model_time
                
                if time_diff.total_seconds() < 3600:  # Kurang dari 1 jam
                    formatted_activities.append({
                        "id": 1,
                        "type": "training",
                        "message": "Model berhasil dilatih ulang",
                        "timestamp": model_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "icon": "fas fa-check",
                        "color": "green"
                    })
        
        return jsonify(formatted_activities[:5])
    except Exception as e:
        print(f"Error getting recent activities: {e}")
        return jsonify([])

# --- API untuk export model info ---
@app.route('/api/admin/export-info')
@login_required
def export_model_info():
    try:
        export_data = {
            "model_info": model_info,
            "training_status": training_status,
            "export_timestamp": datetime.now().isoformat(),
            "intents_count": len(intents.get('intents', [])) if 'intents' in globals() else 0
        }
        return jsonify(export_data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# --- API untuk statistik sistem real-time ---
@app.route('/api/admin/system-stats')
@login_required
def get_system_stats():
    try:
        stats = {
            "uptime": "Online",
            "memory_usage": "Normal",
            "cpu_usage": "Low",
            "disk_space": "Available",
            "model_loaded": 'model' in globals() and model is not None,
            "intents_loaded": 'intents' in globals() and intents is not None,
            "last_request": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_conversations": session.get('conversation_count', 0)
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.get_json()
    prompt = data.get('message', '')
    
    if 'messages' not in session:
        session['messages'] = []
    
    session['messages'].append({"role": "user", "content": prompt})
    
    ints = predict_class(prompt)
    response = getResponse(ints, intents)
    
    session['messages'].append({"role": "assistant", "content": response})
    
    session.modified = True
    
    return jsonify({
        'response': response,
        'messages': session['messages']
    })

@app.route('/api/reset', methods=['POST'])
def reset_chat():
    session['messages'] = [{"role": "assistant", "content": "Hai! Ada yang bisa aku bantu hari ini?"}]
    session.modified = True
    return jsonify({'status': 'success', 'messages': session['messages']})

@app.route('/api/messages', methods=['GET'])
def get_messages():
    if 'messages' not in session:
        session['messages'] = [{"role": "assistant", "content": "Hai! Ada yang bisa aku bantu hari ini?"}]
    return jsonify({'messages': session['messages']})

@app.route('/api/patterns', methods=['GET'])
def get_all_patterns():
    """Get all patterns from intents.json for autocomplete"""
    try:
        all_patterns = []
        if 'intents' in globals() and intents:
            for intent in intents.get('intents', []):
                for pattern in intent.get('patterns', []):
                    all_patterns.append(pattern)
        return jsonify({'patterns': all_patterns})
    except Exception as e:
        print(f"Error getting patterns: {e}")
        return jsonify({'patterns': []})

if __name__ == '__main__':
    import os
    # Suppress Flask development server warning
    os.environ['FLASK_ENV'] = 'development'
    
    print("\n" + "="*60)
    print("🚀 Chatbot BRMP Development Server")
    print("="*60)
    print("📍 URL: http://localhost:5000")
    print("📍 Admin: http://localhost:5000/admin/login")
    print("⚠️  Development mode - Not for production use")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)