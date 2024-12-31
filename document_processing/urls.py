from django.urls import path, include
from . import views

urlpatterns = [
    path('accounts/', include('django.contrib.auth.urls')),  # For login/logout
    path('register/', views.register, name='register'),
    path('upload/', views.upload_document, name='upload_document'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('document/<int:document_id>/', views.document_detail, name='document_detail'),
    path('export/<int:document_id>/', views.export_document, name='export_document'),


    # Add other paths as needed
]

