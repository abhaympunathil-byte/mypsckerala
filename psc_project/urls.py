from django.contrib import admin
from django.urls import path, include
from my_psc_kerala.admin import admin_site

urlpatterns = [
    path('admin/', admin_site.urls),
    path('', include('my_psc_kerala.urls')),
]
