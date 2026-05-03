"""
URL configuration for tech_site project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.views.static import serve
from django.views.generic import RedirectView
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('robots.txt', RedirectView.as_view(url='/static/robots.txt', permanent=True)),
    path('', include('catalog.urls')),
]

# Serve local image files from all last_* and dish folders dynamically
def serve_product_folders(request, folder, path):
    folder_path = os.path.join(settings.BASE_DIR, folder)
    allowed_folders = ['dish']
    is_allowed = folder.startswith('last_') or folder in allowed_folders
    
    if not is_allowed or not os.path.isdir(folder_path):
        from django.http import Http404
        raise Http404("Folder not found")
    return serve(request, path, document_root=folder_path)

if settings.DEBUG:
    urlpatterns += [
        path(f'{settings.MEDIA_URL.lstrip("/")}<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
        path('<str:folder>/<path:path>', serve_product_folders),
    ]
