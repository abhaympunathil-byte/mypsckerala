from django.urls import path
from my_psc_kerala import views

urlpatterns = [
    # Auth paths
    path('register/', views.register_view, name='register'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # App paths
    path('', views.dashboard_view, name='dashboard'),
    path('class/<int:class_id>/', views.subjects_view, name='subjects'),
    path('subject/<int:subject_id>/', views.exam_view, name='exam'),
    path('profile/', views.profile_view, name='profile'),
    
    # API endpoints
    path('api/attempts/', views.MCQAttemptView.as_view(), name='api_attempts'),
]
