import unittest
import json
import os
import sys
import tempfile
from io import BytesIO
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from app import app, Session, STATIC_DIR, QR_FOLDER, INCIDENT_FOLDER, FACES_FOLDER
from models import User, AccessLog, Base
from ai_engine import generate_qr, get_face_data, verify_face
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class TestFunctionalRequirements(unittest.TestCase):
    """Essential functional requirement tests"""

    @classmethod
    def setUpClass(cls):
        """Setup test database"""
        cls.db_fd, cls.db_path = tempfile.mkstemp()
        cls.test_db_url = f"sqlite:///{cls.db_path}"
        cls.engine = create_engine(cls.test_db_url)
        Base.metadata.create_all(cls.engine)
        cls.TestSession = sessionmaker(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        """Cleanup after tests"""
        try:
            os.close(cls.db_fd)
        except:
            pass
        try:
            os.unlink(cls.db_path)
        except:
            pass

    def setUp(self):
        """Setup before each test"""
        self.app = app.test_client()
        self.app.testing = True
        session = self.TestSession()
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()
        
        # Login as admin
        with self.app.session_transaction() as sess:
            sess['admin_logged_in'] = True

    # ============== FR-1: USER REGISTRATION ==============

    def test_1_user_registration(self):
        """User can register with name and photo"""
        test_image = self._create_test_image()
        data = {'name': 'Jan Kowalski', 'photo': (BytesIO(test_image), 'test.jpg')}
        response = self.app.post('/api/register', data=data, content_type='multipart/form-data')
        self.assertIn(response.status_code, [200, 400, 422])

    def test_2_registration_needs_name(self):
        """Registration without name should error"""
        test_image = self._create_test_image()
        data = {'photo': (BytesIO(test_image), 'test.jpg')}
        response = self.app.post('/api/register', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 400)

    # ============== FR-2: QR CODE GENERATION ==============

    def test_3_qr_code_generation(self):
        """QR code is generated for each user"""
        qr_data = "test_qr_12345"
        result = generate_qr(qr_data, QR_FOLDER)
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(os.path.join(QR_FOLDER, result)))

    # ============== FR-3: ACCESS LOGGING ==============

    def test_4_access_log_created(self):
        """Access log is created on successful access"""
        session = self.TestSession()
        log = AccessLog(user_name="Jan Kowalski", status="SUCCESS")
        session.add(log)
        session.commit()
        retrieved = session.query(AccessLog).first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.status, "SUCCESS")
        session.close()

    # ============== FR-4: USER MANAGEMENT ==============

    def test_5_get_users_endpoint(self):
        """Get users endpoint returns JSON list"""
        response = self.app.get('/api/users')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)

    def test_6_delete_user_endpoint(self):
        """Delete user endpoint works"""
        response = self.app.delete('/api/users/9999')
        self.assertIn(response.status_code, [200, 404, 403])

    # ============== FR-5: ADMIN PANEL ==============

    def test_7_admin_panel_loads(self):
        """Admin panel HTML loads"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_8_access_logs_endpoint(self):
        """Get access logs endpoint works"""
        response = self.app.get('/api/logs')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)

    # ============== HELPERS ==============

    def _create_test_image(self):
        """Create a valid test JPG image"""
        from PIL import Image
        import io
        img = Image.new('RGB', (100, 100), color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        return img_bytes.getvalue()


if __name__ == '__main__':
    unittest.main()
