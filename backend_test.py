#!/usr/bin/env python3
import requests
import json
import unittest
import uuid
import time
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://5b0f9f2f-5779-40f1-a547-6f3799a80ed9.preview.emergentagent.com/api"

class XgenCloudAPITest(unittest.TestCase):
    """Test suite for Xgen Cloud API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        # Generate unique test user data
        unique_id = str(uuid.uuid4())[:8]
        self.test_user = {
            "name": f"Test User {unique_id}",
            "email": f"test.user.{unique_id}@example.com",
            "password": "SecurePassword123!"
        }
        self.test_contact = {
            "name": "Contact Test User",
            "email": "contact.test@example.com",
            "message": "This is a test message from the automated test suite."
        }
        self.access_token = None
        self.user_id = None
    
    def test_01_health_check(self):
        """Test health check endpoint"""
        print("\n🔍 Testing Health Check API...")
        response = requests.get(f"{BASE_URL}/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue("database" in data)
        self.assertTrue("timestamp" in data)
        print("✅ Health Check API is working")
    
    def test_02_register_user(self):
        """Test user registration endpoint"""
        print("\n🔍 Testing User Registration API...")
        
        # Test valid registration
        response = requests.post(
            f"{BASE_URL}/register",
            json=self.test_user
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify response structure
        self.assertTrue("access_token" in data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertTrue("user" in data)
        self.assertTrue("id" in data["user"])
        self.assertEqual(data["user"]["name"], self.test_user["name"])
        self.assertEqual(data["user"]["email"], self.test_user["email"])
        
        # Save token and user ID for later tests
        self.access_token = data["access_token"]
        self.user_id = data["user"]["id"]
        
        # Test duplicate email registration
        response = requests.post(
            f"{BASE_URL}/register",
            json=self.test_user
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue("Email already registered" in response.json()["detail"])
        
        # Test invalid email format
        invalid_user = self.test_user.copy()
        invalid_user["email"] = "invalid-email"
        response = requests.post(
            f"{BASE_URL}/register",
            json=invalid_user
        )
        self.assertEqual(response.status_code, 422)  # Validation error
        
        print("✅ User Registration API is working")
    
    def test_03_login_user(self):
        """Test user login endpoint"""
        print("\n🔍 Testing User Login API...")
        
        # Create a new user specifically for login test
        login_user = {
            "name": f"Login Test User {str(uuid.uuid4())[:8]}",
            "email": f"login.test.{str(uuid.uuid4())[:8]}@example.com",
            "password": "LoginPassword123!"
        }
        
        # Register the login test user
        register_response = requests.post(
            f"{BASE_URL}/register",
            json=login_user
        )
        self.assertEqual(register_response.status_code, 200)
        register_data = register_response.json()
        
        # Test valid login with the newly created user
        response = requests.post(
            f"{BASE_URL}/login",
            json={
                "email": login_user["email"],
                "password": login_user["password"]
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify response structure
        self.assertTrue("access_token" in data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertTrue("user" in data)
        self.assertEqual(data["user"]["email"], login_user["email"])
        
        # Save token for authentication test
        self.access_token = data["access_token"]
        
        # Test invalid credentials
        response = requests.post(
            f"{BASE_URL}/login",
            json={
                "email": login_user["email"],
                "password": "WrongPassword123!"
            }
        )
        self.assertEqual(response.status_code, 401)
        self.assertTrue("Incorrect email or password" in response.json()["detail"])
        
        # Test non-existent user
        response = requests.post(
            f"{BASE_URL}/login",
            json={
                "email": f"nonexistent.{uuid.uuid4()}@example.com",
                "password": "AnyPassword123!"
            }
        )
        self.assertEqual(response.status_code, 401)
        self.assertTrue("Incorrect email or password" in response.json()["detail"])
        
        print("✅ User Login API is working")
    
    def test_04_authentication_middleware(self):
        """Test authentication middleware via profile endpoint"""
        print("\n🔍 Testing Authentication Middleware...")
        
        if not self.access_token:
            # If previous test failed, create a new user and get token
            auth_user = {
                "name": f"Auth Test User {str(uuid.uuid4())[:8]}",
                "email": f"auth.test.{str(uuid.uuid4())[:8]}@example.com",
                "password": "AuthPassword123!"
            }
            
            register_response = requests.post(
                f"{BASE_URL}/register",
                json=auth_user
            )
            self.assertEqual(register_response.status_code, 200)
            self.access_token = register_response.json()["access_token"]
        
        # Test with valid token
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(f"{BASE_URL}/profile", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify user data structure
        self.assertTrue("id" in data)
        self.assertTrue("name" in data)
        self.assertTrue("email" in data)
        
        # Test with invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = requests.get(f"{BASE_URL}/profile", headers=headers)
        self.assertEqual(response.status_code, 401)
        
        # Test with missing token
        response = requests.get(f"{BASE_URL}/profile")
        self.assertEqual(response.status_code, 403)  # Forbidden or Unauthorized
        
        print("✅ Authentication Middleware is working")
    
    def test_05_contact_form(self):
        """Test contact form submission endpoint"""
        print("\n🔍 Testing Contact Form API...")
        
        # Test valid submission
        response = requests.post(
            f"{BASE_URL}/contact",
            json=self.test_contact
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify response
        self.assertTrue("message" in data)
        self.assertTrue("id" in data)
        
        # Test invalid email
        invalid_contact = self.test_contact.copy()
        invalid_contact["email"] = "invalid-email"
        response = requests.post(
            f"{BASE_URL}/contact",
            json=invalid_contact
        )
        self.assertEqual(response.status_code, 422)  # Validation error
        
        # Test missing required fields
        for field in ["name", "email", "message"]:
            invalid_contact = self.test_contact.copy()
            del invalid_contact[field]
            response = requests.post(
                f"{BASE_URL}/contact",
                json=invalid_contact
            )
            self.assertEqual(response.status_code, 422)  # Validation error
        
        print("✅ Contact Form API is working")
    
    def test_06_services_api(self):
        """Test services information endpoint"""
        print("\n🔍 Testing Services API...")
        
        response = requests.get(f"{BASE_URL}/services")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify response structure
        self.assertTrue("services" in data)
        self.assertEqual(len(data["services"]), 3)  # Three service categories
        
        # Verify service categories
        service_ids = [service["id"] for service in data["services"]]
        self.assertIn("telecom", service_ids)
        self.assertIn("cloud", service_ids)
        self.assertIn("marketing", service_ids)
        
        # Verify service data structure
        for service in data["services"]:
            self.assertTrue("id" in service)
            self.assertTrue("name" in service)
            self.assertTrue("description" in service)
            self.assertTrue("features" in service)
            self.assertTrue(isinstance(service["features"], list))
        
        print("✅ Services API is working")
    
    def test_07_partners_api(self):
        """Test partners information endpoint"""
        print("\n🔍 Testing Partners API...")
        
        response = requests.get(f"{BASE_URL}/partners")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify response structure
        self.assertTrue("partners" in data)
        self.assertEqual(len(data["partners"]), 4)  # Four partners
        
        # Verify partner companies
        partner_ids = [partner["id"] for partner in data["partners"]]
        self.assertIn("tata-tele", partner_ids)
        self.assertIn("jio", partner_ids)
        self.assertIn("vi", partner_ids)
        self.assertIn("microsoft", partner_ids)
        
        # Verify partner data structure
        for partner in data["partners"]:
            self.assertTrue("id" in partner)
            self.assertTrue("name" in partner)
            self.assertTrue("description" in partner)
            self.assertTrue("industry" in partner)
            self.assertTrue("partnership_since" in partner)
        
        print("✅ Partners API is working")

if __name__ == "__main__":
    print(f"🚀 Starting Xgen Cloud API Tests against {BASE_URL}")
    unittest.main(verbosity=2)