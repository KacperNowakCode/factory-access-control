from flask import Flask, request, jsonify
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
def get_users():
    session = Session()
    users = session.query(User).all()
    # Kopiujemy dane do listy słowników przed zamknięciem sesji
    result = [{"id": u.id, "name": u.name, "qr": u.qr_code_data, "photo": u.photo_path} for u in users]
    session.close()
    return jsonify(result)

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    session = Session()
    user = session.query(User).get(user_id)
    if user:
        session.delete(user)
        session.commit()
    session.close()
    return jsonify({"message": "Usunięto"})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    session = Session()
    logs = session.query(AccessLog).order_by(AccessLog.timestamp.desc()).limit(50).all()
    # Kopiujemy dane do listy słowników przed zamknięciem sesji
    result = [{
        "time": str(l.timestamp), 
        "user": l.user_name, 
        "status": l.status, 
        "snapshot": f"/static/incidents/{l.snapshot_path}" if l.snapshot_path else None
    } for l in logs]
    session.close()
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)