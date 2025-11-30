from django.urls import path
from .views import cp_list, cp_detail, cp_upload, cp_create, cp_edit, cp_upload_analyze, cp_upload_preview, cp_upload_errors_csv

app_name = 'channel_partners'

urlpatterns = [
    path('', cp_list, name='list'),
    path('upload/', cp_upload, name='upload'),
    path('upload/analyze/', cp_upload_analyze, name='upload_analyze'),
    path('upload/preview/', cp_upload_preview, name='upload_preview'),
    path('upload/errors/<str:session_id>/', cp_upload_errors_csv, name='upload_errors_csv'),
    path('create/', cp_create, name='create'),
    path('<int:pk>/', cp_detail, name='detail'),
    path('<int:pk>/edit/', cp_edit, name='edit'),
]

