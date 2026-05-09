import unittest
import json
from web import create_app, db
from web.models import User, Client
from flask_login import login_user

class DashboardTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        
        with self.app.app_context():
            # The create_app already calls db.create_all() and migrate_db()
            # But let's be sure for in-memory DB
            db.create_all()
            
            # Create a test user with hashed password
            from werkzeug.security import generate_password_hash
            user = User(username='admin', email='admin@test.com', password=generate_password_hash('password'))
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self):
        return self.client.post('/login', data=dict(
            email='admin@test.com',
            password='password'
        ), follow_redirects=True)

    def test_api_clients_unauthorized(self):
        response = self.client.get('/api/clients')
        self.assertEqual(response.status_code, 401)

    def test_api_clients_authorized(self):
        with self.client:
            self.login()
            # Add a test client within app context
            with self.app.app_context():
                client = Client(client_id='test_hwid', version='1.0.0', status='Active', name='Test Name')
                db.session.add(client)
                db.session.commit()
                
            response = self.client.get('/api/clients')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['client_id'], 'test_hwid')
            self.assertEqual(data[0]['name'], 'Test Name')

    def test_api_licenses_unauthorized(self):
        response = self.client.get('/api/licenses')
        self.assertEqual(response.status_code, 401)

    def test_dashboard_page_unauthorized(self):
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 302) # Redirect to login

    def test_dashboard_page_authorized(self):
        with self.client:
            self.login()
            response = self.client.get('/dashboard')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Dashboard', response.data)

if __name__ == '__main__':
    unittest.main()
