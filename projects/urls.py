from django.urls import path
from .views import project_list, project_create, project_detail, project_edit, migrate_leads, unit_selection, assign_employees

app_name = 'projects'

urlpatterns = [
    path('', project_list, name='list'),
    path('create/', project_create, name='create'),
    path('<int:pk>/', project_detail, name='detail'),
    path('<int:pk>/edit/', project_edit, name='edit'),
    path('<int:pk>/migrate-leads/', migrate_leads, name='migrate_leads'),
    path('<int:pk>/units/', unit_selection, name='unit_selection'),
    path('<int:pk>/assign-employees/', assign_employees, name='assign_employees'),
]

