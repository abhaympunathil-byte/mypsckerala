from django.urls import path
from my_psc_kerala import views

urlpatterns = [
    # Auth paths
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Google Auth paths
    path('auth/google/login/', views.google_login_view, name='google_login'),
    path('auth/google/callback/', views.google_callback_view, name='google_callback'),
    
    # App paths
    path('', views.index_view, name='index'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('about/', views.about_view, name='about'),
    path('upload-materials/', views.upload_materials_view, name='upload_materials'),
    path('class/<int:class_id>/', views.subjects_view, name='subjects'),
    path('subject/<int:subject_id>/', views.exam_view, name='exam'),
    path('profile/', views.profile_view, name='profile'),
    path('previous-papers/', views.previous_papers_view, name='previous_papers'),
    
    # Live Mock Exams paths
    path('live-exams/', views.live_exams_list_view, name='live_exams'),
    path('live-exam/<int:test_id>/', views.live_exam_session_view, name='live_exam_session'),
    
    # API endpoints
    path('api/attempts/', views.MCQAttemptView.as_view(), name='api_attempts'),
    path('api/live-exam/submit/', views.SubmitLiveExamAPIView.as_view(), name='api_live_exam_submit'),
]
