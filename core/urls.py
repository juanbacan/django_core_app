from django.urls import include, path
from .views_admin import *

app_name = 'core'

urlpatterns = [
    path('loginModal/', LoginModalView.as_view(), name='loginModal'),
    path('model_autocomplete/', ModelAutocompleteView.as_view(), name='model_autocomplete'),
    path('api/', api, name='api_administracion'), 
    path('upload_image/', upload_image, name='upload_image'),
    path('custom_user_autocomplete/', CustomUserAutocompleteView.as_view(), name='custom_user_autocomplete'),
]