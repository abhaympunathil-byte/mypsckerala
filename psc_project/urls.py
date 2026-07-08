from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from my_psc_kerala.admin import admin_site

urlpatterns = [
    path('admin/', admin_site.urls),
    path('', include('my_psc_kerala.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
