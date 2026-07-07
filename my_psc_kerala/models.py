from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils import timezone

class PSCUserManager(BaseUserManager):
    def create_user(self, email, full_name, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, full_name, password, **extra_fields)

class PSCUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = PSCUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    def __str__(self):
        return self.email

class OTPVerification(models.Model):
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)

    def is_expired(self):
        # OTP valid for 10 minutes
        return timezone.now() > self.created_at + timezone.timedelta(minutes=10)

    def __str__(self):
        return f"{self.email} - {self.otp_code} - Verified: {self.is_verified}"

class ClassLevel(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Subject(models.Model):
    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('class_level', 'name')

    def __str__(self):
        return f"{self.name} ({self.class_level.name})"

class StudyNote(models.Model):
    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE, related_name='study_notes')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='study_notes')
    title = models.CharField(max_length=255)
    content = models.TextField(help_text="Rich text content")

    def __str__(self):
        return f"{self.title} - {self.subject.name}"

class Question(models.Model):
    ANSWER_CHOICES = [
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
    ]
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_answer = models.CharField(max_length=1, choices=ANSWER_CHOICES)
    explanation = models.TextField()

    def __str__(self):
        return f"Question {self.id}: {self.question_text[:50]}..."

class UserPerformance(models.Model):
    user = models.ForeignKey(PSCUser, on_delete=models.CASCADE, related_name='performances')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='attempts')
    is_correct = models.BooleanField()
    attempted_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - Q{self.question.id} - Correct: {self.is_correct}"
