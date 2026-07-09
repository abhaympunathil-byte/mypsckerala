import random
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from urllib.parse import urlencode
import requests

# DRF imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from my_psc_kerala.models import (
    PSCUser, OTPVerification, ClassLevel, Subject, StudyNote, Question, UserPerformance,
    MockTest, MockTestAttempt, UserUpload
)
from my_psc_kerala.serializers import MCQAttemptSerializer


# --- AUTHENTICATION VIEWS ---

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        
        if not full_name or not email or not password:
            messages.error(request, "All fields are required.")
            return render(request, 'register.html')
            
        try:
            # Check if user already exists
            user = PSCUser.objects.filter(email=email).first()
            if user:
                if user.is_active:
                    messages.error(request, "This email is already registered and active. Please log in.")
                    return redirect('login')
                else:
                    # Update details for inactive user and send new OTP
                    user.full_name = full_name
                    user.set_password(password)
                    user.save()
            else:
                # Create inactive user
                user = PSCUser.objects.create_user(
                    email=email,
                    full_name=full_name,
                    password=password,
                    is_active=False
                )
            
            # Generate 6-digit OTP
            otp = f"{random.randint(100000, 999999)}"
            
            # Save or update OTP
            otp_obj, created = OTPVerification.objects.update_or_create(
                email=email,
                defaults={'otp_code': otp, 'is_verified': False, 'created_at': timezone.now()}
            )
            
            # Send Email (console by default)
            send_mail(
                'Verify Your Account - My PSC Kerala',
                f'Hello {full_name},\n\nYour OTP for verifying your My PSC Kerala account is: {otp}\n\nThis OTP is valid for 10 minutes.',
                'noreply@mypsckerala.com',
                [email],
                fail_silently=False,
            )
            
            # Store email in session to verify
            request.session['verify_email'] = email
            messages.success(request, "An OTP has been sent to your email. Please verify.")
            return redirect('verify_otp')
            
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            
    return render(request, 'register.html')


def verify_otp_view(request):
    email = request.session.get('verify_email')
    if not email:
        messages.error(request, "No email session found. Please register first.")
        return redirect('register')
        
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code', '').strip()
        
        if not otp_code:
            messages.error(request, "Please enter the OTP.")
            return render(request, 'verify_otp.html', {'email': email})
            
        # Get latest OTP verification record
        otp_record = OTPVerification.objects.filter(email=email, is_verified=False).order_by('-created_at').first()
        
        if not otp_record:
            messages.error(request, "No OTP record found. Please register again.")
            return redirect('register')
            
        if otp_record.is_expired():
            messages.error(request, "OTP has expired. Please register/request a new one.")
            return render(request, 'verify_otp.html', {'email': email})
            
        if otp_record.otp_code == otp_code:
            # Mark OTP as verified
            otp_record.is_verified = True
            otp_record.save()
            
            # Activate user
            try:
                user = PSCUser.objects.get(email=email)
                user.is_active = True
                user.save()
                
                # Log the user in
                # Specify authentication backend explicitly
                login(request, user, backend='my_psc_kerala.auth_backends.EmailAuthBackend')
                
                # Clear session
                del request.session['verify_email']
                
                messages.success(request, f"Welcome {user.full_name}! Your account has been verified successfully.")
                return redirect('dashboard')
            except PSCUser.DoesNotExist:
                messages.error(request, "User account not found. Please register again.")
                return redirect('register')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            
    return render(request, 'verify_otp.html', {'email': email})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        
        if not email or not password:
            messages.error(request, "Please fill in all fields.")
            return render(request, 'login.html')
            
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, f"Welcome back, {user.full_name}!")
                return redirect('dashboard')
            else:
                # User is inactive, send a new OTP and redirect to verify
                otp = f"{random.randint(100000, 999999)}"
                OTPVerification.objects.update_or_create(
                    email=user.email,
                    defaults={'otp_code': otp, 'is_verified': False, 'created_at': timezone.now()}
                )
                send_mail(
                    'Verify Your Account - My PSC Kerala',
                    f'Hello {user.full_name},\n\nYour OTP for verifying your My PSC Kerala account is: {otp}\n\nThis OTP is valid for 10 minutes.',
                    'noreply@mypsckerala.com',
                    [user.email],
                    fail_silently=False,
                )
                request.session['verify_email'] = user.email
                messages.warning(request, "Your account is not active. We have sent a new OTP to your email.")
                return redirect('verify_otp')
        else:
            messages.error(request, "Invalid email or password.")
            
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')


# --- APPLICATION FLOW VIEWS ---

def index_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'index.html')

def about_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        message = request.POST.get('message', '').strip()
        
        if name and email and message:
            try:
                subject = f"Contact Form Submission from {name}"
                body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
                send_mail(
                    subject,
                    body,
                    'mypsc26@gmail.com',  # From
                    ['mypsc26@gmail.com'],  # To
                    fail_silently=False,
                )
                messages.success(request, "Your message has been sent successfully. We'll be in touch soon!")
            except Exception as e:
                messages.error(request, "Sorry, an error occurred while sending your message. Please try again.")
        else:
            messages.error(request, "Please fill in all the fields.")
            
        return redirect('about')

    return render(request, 'about.html')

@login_required
def upload_materials_view(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        upload_type = request.POST.get('upload_type')
        uploaded_file = request.FILES.get('file')
        
        if title and upload_type and uploaded_file:
            UserUpload.objects.create(
                user=request.user,
                title=title,
                upload_type=upload_type,
                file=uploaded_file
            )
            messages.success(request, "Your material has been uploaded successfully and is pending admin approval!")
            return redirect('upload_materials')
        else:
            messages.error(request, "Please provide title, upload type, and select a file.")
            
    # Get user's previous uploads
    user_uploads = UserUpload.objects.filter(user=request.user).order_by('-uploaded_at')
    
    return render(request, 'upload_materials.html', {'user_uploads': user_uploads})

@login_required
def dashboard_view(request):
    class_levels = ClassLevel.objects.all().order_by('name')
    return render(request, 'dashboard.html', {'class_levels': class_levels})


@login_required
def subjects_view(request, class_id):
    try:
        class_level = ClassLevel.objects.get(pk=class_id)
    except ClassLevel.DoesNotExist:
        messages.error(request, "Class Level not found.")
        return redirect('dashboard')
        
    subjects = class_level.subjects.all().order_by('name')
    study_notes = class_level.study_notes.all().order_by('title')
    
    context = {
        'class_level': class_level,
        'subjects': subjects,
        'study_notes': study_notes
    }
    return render(request, 'subjects.html', context)


@login_required
def exam_view(request, subject_id):
    try:
        subject = Subject.objects.get(pk=subject_id)
    except Subject.DoesNotExist:
        messages.error(request, "Subject not found.")
        return redirect('dashboard')
        
    questions = subject.questions.all().order_by('id')
    
    if not questions.exists():
        messages.warning(request, f"No questions available for {subject.name} yet.")
        return redirect('subjects', class_id=subject.class_level.id)
        
    return render(request, 'exam.html', {'subject': subject, 'questions': questions})


@login_required
def profile_view(request):
    user = request.user
    attempts = UserPerformance.objects.filter(user=user)
    mock_attempts = MockTestAttempt.objects.filter(user=user).order_by('-attempted_date')
    
    total_attempted = attempts.count()
    correct_attempts = attempts.filter(is_correct=True).count()
    accuracy = round((correct_attempts / total_attempted * 100), 2) if total_attempted > 0 else 0
    
    mock_tests_count = mock_attempts.count()
    # Dynamic hours studied formula: 3 minutes per practice MCQ + 45 minutes per mock test
    total_minutes = (total_attempted * 3) + (mock_tests_count * 45)
    hours_studied = round(total_minutes / 60, 1)
    
    # Subject-wise statistics
    subject_stats = attempts.values('question__subject__name').annotate(
        total=Count('id'),
        correct=Count('id', filter=Q(is_correct=True))
    )
    
    subject_wise_data = []
    subject_labels = []
    subject_accuracy = []
    subject_totals = []
    
    for stat in subject_stats:
        subj_name = stat['question__subject__name']
        total = stat['total']
        correct = stat['correct']
        acc = round((correct / total * 100), 2) if total > 0 else 0
        
        subject_wise_data.append({
            'subject': subj_name,
            'total': total,
            'correct': correct,
            'accuracy': acc
        })
        subject_labels.append(subj_name)
        subject_accuracy.append(acc)
        subject_totals.append(total)
        
    # JSON strings for Chart.js
    chart_labels_json = json.dumps(subject_labels)
    chart_accuracy_json = json.dumps(subject_accuracy)
    chart_totals_json = json.dumps(subject_totals)
    
    context = {
        'total_attempted': total_attempted,
        'correct_attempts': correct_attempts,
        'accuracy': accuracy,
        'mock_tests_count': mock_tests_count,
        'hours_studied': hours_studied,
        'subject_wise_data': subject_wise_data,
        'mock_attempts': mock_attempts,
        'chart_labels': chart_labels_json,
        'chart_accuracy': chart_accuracy_json,
        'chart_totals': chart_totals_json
    }
    return render(request, 'profile.html', context)


@login_required
def live_exams_list_view(request):
    mock_tests = MockTest.objects.all().order_by('name')
    # Fetch high scores for each test for the current user
    user_attempts = MockTestAttempt.objects.filter(user=request.user)
    
    test_list_data = []
    for test in mock_tests:
        test_attempts = user_attempts.filter(mock_test=test)
        high_score = None
        has_attempted = test_attempts.exists()
        if has_attempted:
            high_score = max([att.score for att in test_attempts])
            
        test_list_data.append({
            'test': test,
            'has_attempted': has_attempted,
            'high_score': high_score,
            'attempts_count': test_attempts.count()
        })
        
    return render(request, 'live_exams_list.html', {'mock_tests': test_list_data})


@login_required
def live_exam_session_view(request, test_id):
    try:
        mock_test = MockTest.objects.get(pk=test_id)
    except MockTest.DoesNotExist:
        messages.error(request, "Mock Test not found.")
        return redirect('live_exams')
        
    questions = mock_test.questions.all().order_by('id')
    if not questions.exists():
        messages.warning(request, "This mock test does not contain questions yet.")
        return redirect('live_exams')
        
    # Render full screen layout (hide standard sidebar)
    context = {
        'mock_test': mock_test,
        'questions': questions,
        'hide_sidebar': True
    }
    return render(request, 'live_exam.html', context)


# --- DRF API VIEWS ---

class MCQAttemptView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = MCQAttemptSerializer(data=request.data)
        if serializer.is_valid():
            question_id = serializer.validated_data['question_id']
            selected_option = serializer.validated_data['selected_option']
            
            try:
                question = Question.objects.get(pk=question_id)
            except Question.DoesNotExist:
                return Response(
                    {"error": "Question not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
                
            # Check correctness
            is_correct = (question.correct_answer == selected_option)
            
            # Save User Attempt
            UserPerformance.objects.create(
                user=request.user,
                question=question,
                is_correct=is_correct
            )
            
            return Response({
                "is_correct": is_correct,
                "correct_answer": question.correct_answer,
                "explanation": question.explanation,
                "selected_option": selected_option
            }, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubmitLiveExamAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        test_id = request.data.get('mock_test_id')
        answers = request.data.get('answers', {})
        
        try:
            mock_test = MockTest.objects.get(pk=test_id)
        except MockTest.DoesNotExist:
            return Response(
                {"error": "Mock Test not found."},
                status=status.HTTP_404_NOT_FOUND
            )
            
        total_correct = 0
        total_wrong = 0
        total_questions = mock_test.questions.count()
        
        for question in mock_test.questions.all():
            q_id_str = str(question.id)
            if q_id_str in answers:
                selected = answers[q_id_str]
                is_correct = (question.correct_answer == selected)
                if is_correct:
                    total_correct += 1
                else:
                    total_wrong += 1
                
                # Also log to standard UserPerformance
                UserPerformance.objects.create(
                    user=request.user,
                    question=question,
                    is_correct=is_correct
                )
                
        # Score calculation: +2.0 for correct, -0.66 penalty for wrong
        score = (total_correct * 2.0) - (total_wrong * 0.66)
        score = round(score, 2)
        
        # Save MockTestAttempt record
        attempt = MockTestAttempt.objects.create(
            user=request.user,
            mock_test=mock_test,
            score=score,
            total_correct=total_correct,
            total_wrong=total_wrong
        )
        
        return Response({
            "attempt_id": attempt.id,
            "score": score,
            "total_correct": total_correct,
            "total_wrong": total_wrong,
            "total_unanswered": total_questions - (total_correct + total_wrong),
            "total_questions": total_questions,
            "accuracy": round((total_correct / (total_correct + total_wrong) * 100), 2) if (total_correct + total_wrong) > 0 else 0
        }, status=status.HTTP_200_OK)


# --- GOOGLE OAUTH2 VIEWS ---

def google_login_view(request):
    google_auth_url = 'https://accounts.google.com/o/oauth2/v2/auth'
    params = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'scope': 'openid email profile',
        'access_type': 'offline',
        'prompt': 'select_account',
    }
    url = f"{google_auth_url}?{urlencode(params)}"
    return redirect(url)

def google_callback_view(request):
    code = request.GET.get('code')
    if not code:
        messages.error(request, 'Google login failed or was cancelled.')
        return redirect('login')

    # Exchange code for token
    token_url = 'https://oauth2.googleapis.com/token'
    data = {
        'code': code,
        'client_id': settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'grant_type': 'authorization_code',
    }
    
    try:
        token_response = requests.post(token_url, data=data)
        token_response.raise_for_status()
        tokens = token_response.json()
        access_token = tokens.get('access_token')

        # Get user info
        user_info_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        user_info_response = requests.get(user_info_url, headers=headers)
        user_info_response.raise_for_status()
        user_info = user_info_response.json()

        email = user_info.get('email')
        full_name = user_info.get('name', 'Google User')

        if not email:
            messages.error(request, 'Could not retrieve email from Google.')
            return redirect('login')

        # Find or create user
        user, created = PSCUser.objects.get_or_create(email=email, defaults={
            'full_name': full_name,
            'is_active': True,
        })
        
        if created:
            user.set_unusable_password()
            user.save()
        elif not user.is_active:
            user.is_active = True
            user.save()

        # Log the user in
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('dashboard')
        
    except requests.exceptions.RequestException as e:
        messages.error(request, 'Failed to authenticate with Google. Please try again.')
        return redirect('login')

