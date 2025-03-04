from django.urls import include, path
from .views import *

app_name = 'core'

urlpatterns = [
    # Third party apps
    path('accounts/', include('allauth.urls')),
    path('tinymce/', include('tinymce.urls')),
    path('webpush/', include('webpush.urls')),
    path('', include('pwa.urls')),

    # Custom apps
    path('custom_user_autocomplete/', CustomUserAutocompleteView.as_view(), name='custom_user_autocomplete'),
    path('model_autocomplete/', ModelAutocompleteView.as_view(), name='model_autocomplete'),
    path('loginModal/', LoginModalView.as_view(), name='loginModal'),
    path('upload_image/', upload_image, name='upload_image'),
    path('api/', api, name='api_administracion'), 
]
