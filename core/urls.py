from django.urls import include, path
from .views import *

app_name = 'core'

urlpatterns = [
    # Third party apps
    path('accounts/', include('allauth.urls')),
    path('tinymce/', include('tinymce.urls')),
    path('webpush/', include('webpush.urls')),
    path('', include('pwa.urls')),
]
