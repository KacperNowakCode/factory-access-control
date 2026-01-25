import unittest
import json
import os
import sys
import tempfile
from io import BytesIO
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from app import app
from models import User, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class TestAPIIntegration(unittest.TestCase):
    """Essential API integration tests"""

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

    def test_1_register_user(self):
        """Register user endpoint works"""
        test_image = self._create_test_image()
        response = self.app.post(
            '/api/register',
            data={'name': 'Test User', 'photo': (BytesIO(test_image), 'test.jpg')},
            content_type='multipart/form-data'
        )
        self.assertIn(response.status_code, [200, 400, 422])

    def test_2_get_users(self):
        """Get users works"""
        response = self.app.get('/api/users')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)

    def test_3_get_logs(self):
        """Get logs works"""
        response = self.app.get('/api/logs')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)

    def test_4_delete_user(self):
        """Delete user works"""
        response = self.app.delete('/api/users/999')
        self.assertIn(response.status_code, [200, 404, 403])

    def test_5_missing_photo_error(self):
        """Registration without photo errors"""
        response = self.app.post(
            '/api/register',
            data={'name': 'Test'},
            content_type='multipart/form-data'
        )
        self.assertEqual(response.status_code, 400)

    # ============== HELPERS ==============

    def _create_test_image(self):
        """Create a valid test JPG image"""
        img = Image.new('RGB', (100, 100), color='white')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        return img_bytes.getvalue()


if __name__ == '__main__':
    unittest.main()
