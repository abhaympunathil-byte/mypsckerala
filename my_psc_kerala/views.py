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

# DRF imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from my_psc_kerala.models import (
    PSCUser, OTPVerification, ClassLevel, Subject, StudyNote, Question, UserPerformance
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
    
    total_attempted = attempts.count()
    correct_attempts = attempts.filter(is_correct=True).count()
    accuracy = round((correct_attempts / total_attempted * 100), 2) if total_attempted > 0 else 0
    
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
        'subject_wise_data': subject_wise_data,
        'chart_labels': chart_labels_json,
        'chart_accuracy': chart_accuracy_json,
        'chart_totals': chart_totals_json
    }
    return render(request, 'profile.html', context)


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
