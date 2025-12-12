import cv2
import qrcode
import os
import numpy as np

def generate_qr(data, output_folder):
    """Generuje plik QR code"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    
    filename = f"{data}.png"
    path = os.path.join(output_folder, filename)
    img.save(path)
    return filename

def get_face_data(image_source):
    """
    Zwraca: (wektor_obrazu, współrzędne_twarzy)
    Współrzędne to krotka: (x, y, w, h)
    """
    img = None
    if hasattr(image_source, 'read'):
        file_bytes = np.frombuffer(image_source.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
        image_source.seek(0)
    else:
        img = cv2.imread(image_source, cv2.IMREAD_GRAYSCALE)
    
    if img is None:
        return None, None

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    # Parametry scaleFactor=1.1, minNeighbors=5 (zwiększone dla pewności)
    faces = face_cascade.detectMultiScale(img, 1.1, 5)
    
    if len(faces) == 0:
        return None, None

    # Bierzemy największą twarz (główną)
    x, y, w, h = faces[0]
    face_roi = img[y:y+h, x:x+w]
    face_roi = cv2.resize(face_roi, (100, 100))

    return face_roi.flatten(), (x, y, w, h)

def verify_face(known_encoding, unknown_image_file):
    """
    Porównuje twarze i zwraca: (czy_sukces, procent_zgodności, koordynaty_twarzy)
    """
    unknown_encoding, face_location = get_face_data(unknown_image_file)

    if unknown_encoding is None:
        return False, 0, None

    if known_encoding is None:
        return False, 0, face_location

    # Oblicz różnicę (MSE)
    err = np.sum((known_encoding.astype("float") - unknown_encoding.astype("float")) ** 2)
    err /= float(known_encoding.shape[0])
    
    # --- KALIBRACJA NA 90% ---
    # MSE=0 to idealna kopia (100%). MSE=3000 to już spora różnica.
    # Wzór: Score = 100 - (Błąd / Dzielnik)
    # Dobieramy dzielnik tak, aby próg akceptacji wypadał w okolicy 90%
    
    # Im mniejszy błąd, tym lepiej.
    # Zakładamy, że błąd 2500 jest "graniczny".
    # 2500 / 250 = 10.  100 - 10 = 90%.
    
    score = 100 - (err / 250)
    score = max(0, min(100, score)) # Ogranicz do zakresu 0-100%

    # Wymagamy >= 90% (zgodnie z dokumentacją)
    is_match = score >= 90.0
    
    return is_match, int(score), face_location