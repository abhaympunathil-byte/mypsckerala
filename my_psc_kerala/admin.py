from django.contrib import admin
from django.contrib.admin import AdminSite
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count
from my_psc_kerala.models import (
    PSCUser, ClassLevel, Subject, StudyNote, Question, UserPerformance, OTPVerification
)
from my_psc_kerala.import_utils import import_data_from_file

class PSCAdminSite(AdminSite):
    site_header = 'My PSC Kerala Administration'
    site_title = 'My PSC Kerala Admin'
    index_title = 'Dashboard & Statistics'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('bulk-import/', self.admin_view(self.bulk_import_view), name='bulk_import'),
        ]
        return custom_urls + urls

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        # Platform statistics
        extra_context['total_users'] = PSCUser.objects.count()
        extra_context['active_users'] = PSCUser.objects.filter(is_active=True).count()
        
        # Total questions per class
        class_stats = ClassLevel.objects.annotate(q_count=Count('subjects__questions'))
        extra_context['class_stats'] = class_stats
        
        return super().index(request, extra_context=extra_context)

    def bulk_import_view(self, request):
        if request.method == 'POST':
            file = request.FILES.get('import_file')
            if not file:
                messages.error(request, "Please upload a CSV or Excel file.")
                return redirect('admin:bulk_import')
                
            # Read uploader contents
            result = import_data_from_file(file.read(), file.name)
            
            if result['success']:
                messages.success(request, f"Successfully imported {result['imported_count']} items!")
            else:
                messages.warning(request, f"Import finished with issues. {result['imported_count']} items imported.")
                
            for err in result['errors']:
                messages.error(request, err)
                
            return redirect('admin:index')
            
        context = dict(
            self.each_context(request),
            title="Bulk Import Questions & Study Notes",
        )
        return render(request, 'admin/bulk_import.html', context)

# Instantiate the custom admin site
admin_site = PSCAdminSite(name='myadmin')

# Register models with our custom admin site
@admin.register(PSCUser, site=admin_site)
class PSCUserAdmin(admin.ModelAdmin):
    list_display = ['email', 'full_name', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['is_active', 'is_staff']
    search_fields = ['email', 'full_name']

@admin.register(ClassLevel, site=admin_site)
class ClassLevelAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Subject, site=admin_site)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'class_level']
    list_filter = ['class_level']
    search_fields = ['name']

@admin.register(StudyNote, site=admin_site)
class StudyNoteAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'class_level']
    list_filter = ['class_level', 'subject']
    search_fields = ['title', 'content']

@admin.register(Question, site=admin_site)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text_short', 'subject', 'correct_answer']
    list_filter = ['subject__class_level', 'subject', 'correct_answer']
    search_fields = ['question_text', 'explanation']

    def question_text_short(self, obj):
        return obj.question_text[:50] + '...' if len(obj.question_text) > 50 else obj.question_text
    question_text_short.short_description = 'Question Text'

@admin.register(UserPerformance, site=admin_site)
class UserPerformanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'question', 'is_correct', 'attempted_date']
    list_filter = ['is_correct', 'attempted_date']
    search_fields = ['user__email', 'question__question_text']

@admin.register(OTPVerification, site=admin_site)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ['email', 'otp_code', 'created_at', 'is_verified']
    list_filter = ['is_verified']
    search_fields = ['email']
