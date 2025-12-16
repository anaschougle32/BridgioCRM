from django.urls import path
from .views import project_list, project_create, project_detail, project_edit, project_delete, project_archive_data, migrate_leads, unit_selection, assign_employees, unit_calculation, search_visited_leads

app_name = 'projects'

urlpatterns = [
    path('', project_list, name='list'),
    path('create/', project_create, name='create'),
    path('<int:pk>/', project_detail, name='detail'),
    path('<int:pk>/edit/', project_edit, name='edit'),
    path('<int:pk>/archive-data/', project_archive_data, name='archive_data'),
    path('<int:pk>/delete/', project_delete, name='delete'),
    path('<int:pk>/migrate-leads/', migrate_leads, name='migrate_leads'),
    path('<int:pk>/units/', unit_selection, name='unit_selection'),
    path('<int:pk>/units/<int:unit_id>/calculate/', unit_calculation, name='unit_calculation'),
    path('<int:pk>/assign-employees/', assign_employees, name='assign_employees'),
    path('<int:pk>/search-visited-leads/', search_visited_leads, name='search_visited_leads'),
]

