from django.urls import path
from .views import project_list, project_create, project_detail, project_edit, migrate_leads

app_name = 'projects'

urlpatterns = [
    path('', project_list, name='list'),
    path('create/', project_create, name='create'),
    path('<int:pk>/', project_detail, name='detail'),
    path('<int:pk>/edit/', project_edit, name='edit'),
    path('<int:pk>/migrate-leads/', migrate_leads, name='migrate_leads'),
]

