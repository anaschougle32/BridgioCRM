from django.urls import path
from .views import mandate_owner_reports

app_name = 'reports'

urlpatterns = [
    path('', mandate_owner_reports, name='mandate_owner_reports'),
]

