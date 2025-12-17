import cv2
import face_recognition
import numpy as np
import os
import qrcode
import pickle

def generate_qr(data, output_folder):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    filename = f"{data}.png"
    img.save(os.path.join(output_folder, filename))
    return filename

def get_face_data(image_source):
    # Wczytanie
    if hasattr(image_source, 'read'):
        image_source.seek(0)
        img = face_recognition.load_image_file(image_source)
    else:
        img = face_recognition.load_image_file(image_source)

    # 1. Znajdź twarz
    face_locations = face_recognition.face_locations(img)
    
    if not face_locations:
        return None, None

    # Pobieramy pierwszą twarz
    top, right, bottom, left = face_locations[0]
    
    # Format (x, y, w, h)
    coords = {
        "x": left,
        "y": top,
        "w": right - left,
        "h": bottom - top
    }

    # 2. Zakoduj cechy
    face_encodings = face_recognition.face_encodings(img, face_locations)
    
    if not face_encodings:
        return None, coords

    return pickle.dumps(face_encodings[0]), coords

def verify_face(known_encoding_pickle, unknown_image_file):
    # Pobierz twarz z kamery
    unknown_encoding_packed, coords = get_face_data(unknown_image_file)

    # Jeśli nie wykryto twarzy na zdjęciu
    if coords is None:
        return False, 0, None

    # Jeśli nie ma wzorca (nieznany QR), ale twarz jest widoczna
    if known_encoding_pickle is None:
        return False, 0, coords

    try:
        known_encoding = pickle.loads(known_encoding_pickle)
        
        if unknown_encoding_packed:
            unknown_encoding = pickle.loads(unknown_encoding_packed)
            
            # Porównanie
            distance = face_recognition.face_distance([known_encoding], unknown_encoding)[0]
            score = int((1.0 - distance) * 100)
            is_match = distance < 0.5 # Próg sukcesu

            return is_match, score, coords
        else:
            return False, 0, coords
            
    except Exception as e:
        print(f"Błąd AI: {e}")
        return False, 0, coords