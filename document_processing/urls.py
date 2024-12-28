# document_processing/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_document, name='upload_document'),
    # Add other paths as needed
]
