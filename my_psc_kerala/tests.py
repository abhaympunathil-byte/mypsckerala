from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from my_psc_kerala.models import PSCUser, OTPVerification, ClassLevel, Subject, Question, UserPerformance
import json

class MyPSCKeralaTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Setup class, subject, and question
        self.class_level = ClassLevel.objects.create(name="Class 10")
        self.subject = Subject.objects.create(class_level=self.class_level, name="Science")
        self.question = Question.objects.create(
            subject=self.subject,
            question_text="What is H2O?",
            option_a="Air",
            option_b="Water",
            option_c="Fire",
            option_d="Earth",
            correct_answer="B",
            explanation="H2O represents Water."
        )
        
        # Test users
        self.email = "learner@example.com"
        self.password = "Secr3tP@ssword"
        self.full_name = "Kishore Kumar"
        
        self.verified_user = PSCUser.objects.create_user(
            email="verified@example.com",
            full_name="Verified Practice User",
            password="verifiedpassword123",
            is_active=True
        )

    def test_user_creation(self):
        """Test PSCUser model fields and settings"""
        user = PSCUser.objects.create_user(
            email="testuser@example.com",
            full_name="Test User",
            password="somepassword123"
        )
        self.assertEqual(user.email, "testuser@example.com")
        self.assertEqual(user.full_name, "Test User")
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_staff)

    def test_registration_flow_otp_sent(self):
        """Test that registering creates inactive user and generates/sends an OTP"""
        url = reverse('register')
        data = {
            'full_name': self.full_name,
            'email': self.email,
            'password': self.password
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302) # Redirect to verify_otp
        
        # Check user created but inactive
        user = PSCUser.objects.get(email=self.email)
        self.assertFalse(user.is_active)
        
        # Check OTP created
        otp_entry = OTPVerification.objects.filter(email=self.email).first()
        self.assertIsNotNone(otp_entry)
        self.assertEqual(len(otp_entry.otp_code), 6)
        self.assertFalse(otp_entry.is_verified)

    def test_otp_verification_flow(self):
        """Test OTP verification activates the user and logs them in"""
        # Step 1: Trigger register to create OTP
        self.client.post(reverse('register'), {
            'full_name': self.full_name,
            'email': self.email,
            'password': self.password
        })
        
        otp_entry = OTPVerification.objects.get(email=self.email)
        
        # Step 2: POST correct OTP code
        session = self.client.session
        session['verify_email'] = self.email
        session.save()
        
        response = self.client.post(reverse('verify_otp'), {
            'otp_code': otp_entry.otp_code
        })
        self.assertEqual(response.status_code, 302) # Redirects to dashboard
        
        # Verify user is now active
        user = PSCUser.objects.get(email=self.email)
        self.assertTrue(user.is_active)

    def test_mcq_attempt_api(self):
        """Test the DRF API for evaluating attempts works for authenticated users"""
        # Login verified user
        self.client.login(username=self.verified_user.email, password="verifiedpassword123")
        
        url = reverse('api_attempts')
        
        # Attempt with correct answer
        data = {
            'question_id': self.question.id,
            'selected_option': 'B'
        }
        response = self.client.post(url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        resp_data = response.json()
        self.assertTrue(resp_data['is_correct'])
        self.assertEqual(resp_data['correct_answer'], 'B')
        self.assertEqual(resp_data['explanation'], self.question.explanation)
        
        # Check that user performance was logged
        perf = UserPerformance.objects.filter(user=self.verified_user, question=self.question).first()
        self.assertIsNotNone(perf)
        self.assertTrue(perf.is_correct)

        # Attempt with wrong answer
        data = {
            'question_id': self.question.id,
            'selected_option': 'A'
        }
        response = self.client.post(url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        resp_data = response.json()
        self.assertFalse(resp_data['is_correct'])
