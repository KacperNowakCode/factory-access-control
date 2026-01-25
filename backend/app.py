from flask import Flask, request, jsonify, session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, AccessLog
from ai_engine import get_face_data, generate_qr, verify_face
from flask_cors import CORS
import os
import uuid
import datetime
from io import BytesIO

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BACKEND_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static')
app.secret_key = 'factory_access_control_secret_key_2026'

# Konfiguracja sesji - trwała sesja na 30 dni
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=30)
app.config['SESSION_COOKIE_SECURE'] = False  # Zmień na True w produkcji z HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

CORS(app)

DB_FILE = f"sqlite:///{os.path.join(BACKEND_DIR, 'faceid_system.db')}"
QR_FOLDER = os.path.join(STATIC_DIR, 'qrcodes')
INCIDENT_FOLDER = os.path.join(STATIC_DIR, 'incidents')
FACES_FOLDER = os.path.join(STATIC_DIR, 'faces')

os.makedirs(QR_FOLDER, exist_ok=True)
os.makedirs(INCIDENT_FOLDER, exist_ok=True)
os.makedirs(FACES_FOLDER, exist_ok=True)

engine = create_engine(DB_FILE)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Decorator do ochrony adminowych endpointów
def admin_required(f):
    """Decorator do ochrony adminowych endpointów"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in', False):
            return jsonify({"error": "Brak autoryzacji"}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/register', methods=['POST'])
def register_user():
    name = request.form.get('name')
    photo = request.files.get('photo')
    if not name or not photo:
        return jsonify({"error": "Brak danych"}), 400

    photo_bytes = BytesIO(photo.read())
    photo.seek(0)
    
    # Pobranie danych twarzy
    encoding_pickle, coords = get_face_data(photo_bytes)
    
    if encoding_pickle is None:
        return jsonify({"error": "Nie wykryto twarzy. Użyj wyraźniejszego zdjęcia."}), 400

    photo_filename = f"{uuid.uuid4()}.jpg"
    photo.seek(0)
    photo.save(os.path.join(FACES_FOLDER, photo_filename))

    qr_data = str(uuid.uuid4())[:8]
    generate_qr(qr_data, QR_FOLDER)

    session = Session()
    new_user = User(
        name=name, 
        qr_code_data=qr_data, 
        face_encoding=encoding_pickle, 
        photo_path=f"/static/faces/{photo_filename}"
    )
    session.add(new_user)
    session.commit()
    session.close()

    return jsonify({"message": "Dodano", "qr_code": qr_data})

@app.route('/api/verify_entry', methods=['POST'])
def verify_entry():
    qr_input = request.form.get('qr_code')
    camera_image = request.files.get('frame')

    session = Session()
    user = session.query(User).filter_by(qr_code_data=qr_input).first()

    # Przypadek 1: Nieznany kod QR
    if not user:
        filename = f"unknown_{uuid.uuid4()}.jpg"
        camera_image.seek(0)
        camera_image.save(os.path.join(INCIDENT_FOLDER, filename))
        
        # Pobieramy współrzędne dla czerwonej ramki
        camera_image.seek(0)
        _, unknown_coords = get_face_data(camera_image)
        
        session.add(AccessLog(user_name="Nieznany QR", status="DENIED_QR", snapshot_path=filename))
        session.commit()
        session.close()
        
        return jsonify({
            "status": "denied", 
            "reason": "Zły kod QR", 
            "score": 0,
            "face_rect": unknown_coords
        }), 403

    # Przypadek 2: Użytkownik znaleziony - weryfikacja twarzy
    
    # WAŻNE: Zapisujemy imię do zmiennej póki sesja jest otwarta!
    user_name_str = user.name 
    
    camera_image.seek(0)
    match, score, face_rect_dict = verify_face(user.face_encoding, camera_image)
    
    # Konwersja prostokąta twarzy na format JSON
    rect_data = None
    if face_rect_dict:
        rect_data = {
            "x": int(face_rect_dict['x']),
            "y": int(face_rect_dict['y']),
            "w": int(face_rect_dict['w']),
            "h": int(face_rect_dict['h'])
        }
    
    safe_score = int(score) if score is not None else 0

    if match:
        session.add(AccessLog(user_name=user_name_str, status="SUCCESS"))
        session.commit()
        session.close() # Zamykamy sesję DOPIERO TUTAJ
        
        return jsonify({
            "status": "success", 
            "user": user_name_str, # Używamy zmiennej string, nie obiektu bazy
            "score": safe_score,
            "face_rect": rect_data
        })
    else:
        timestamp = datetime.datetime.now().strftime("%H%M%S")
        filename = f"fail_{user_name_str}_{timestamp}.jpg"
        camera_image.seek(0)
        camera_image.save(os.path.join(INCIDENT_FOLDER, filename))
        
        session.add(AccessLog(
            user_name=user_name_str, 
            status="DENIED_FACE", 
            snapshot_path=filename
        ))
        session.commit()
        session.close() # Zamykamy sesję DOPIERO TUTAJ
        
        return jsonify({
            "status": "denied", 
            "reason": f"Niska zgodność ({safe_score}%)", 
            "score": safe_score,
            "face_rect": rect_data
        }), 403

@app.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    session_db = Session()
    users = session_db.query(User).all()
    # Kopiujemy dane do listy słowników przed zamknięciem sesji
    result = [{"id": u.id, "name": u.name, "qr": u.qr_code_data, "photo": u.photo_path} for u in users]
    session_db.close()
    return jsonify(result)

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    session_db = Session()
    user = session_db.query(User).get(user_id)
    if user:
        session_db.delete(user)
        session_db.commit()
    session_db.close()
    return jsonify({"message": "Usunięto"})

@app.route('/api/logs', methods=['GET'])
@admin_required
def get_logs():
    session_db = Session()
    logs = session_db.query(AccessLog).order_by(AccessLog.timestamp.desc()).limit(50).all()
    # Kopiujemy dane do listy słowników przed zamknięciem sesji
    result = [{
        "id": l.id,
        "time": str(l.timestamp), 
        "user": l.user_name, 
        "status": l.status, 
        "snapshot": f"/static/incidents/{l.snapshot_path}" if l.snapshot_path else None
    } for l in logs]
    session_db.close()
    return jsonify(result)

@app.route('/api/logs/<int:log_id>', methods=['GET'])
@admin_required
def get_log_detail(log_id):
    """Pobranie szczegółów konkretnego logu z snapshot'em"""
    session_db = Session()
    log = session_db.query(AccessLog).filter(AccessLog.id == log_id).first()
    session_db.close()
    
    if not log:
        return jsonify({"error": "Log nie znaleziony"}), 404
    
    return jsonify({
        "id": log.id,
        "time": str(log.timestamp),
        "user": log.user_name,
        "status": log.status,
        "snapshot": f"/static/incidents/{log.snapshot_path}" if log.snapshot_path else None
    })

@app.route('/')
def home():
    return app.send_static_file('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    """Login endpoint dla panelu administratora"""
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    
    # Walidacja (admin/admin)
    if username == 'admin' and password == 'admin':
        session.permanent = True  # Ustawia trwałą sesję
        session['admin_logged_in'] = True
        return jsonify({"message": "Zalogowano", "success": True})
    else:
        return jsonify({"message": "Błędne dane logowania", "success": False}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout endpoint"""
    session.pop('admin_logged_in', None)
    return jsonify({"message": "Wylogowano"})

@app.route('/api/check-admin', methods=['GET'])
def check_admin():
    """Sprawdzenie, czy użytkownik jest zalogowany"""
    is_logged = session.get('admin_logged_in', False)
    return jsonify({"admin_logged_in": is_logged})

if __name__ == '__main__':
    app.run(debug=True, port=5000)