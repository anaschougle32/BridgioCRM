from django.urls import path
from .views import mandate_owner_reports, employee_performance, cp_performance

app_name = 'reports'

urlpatterns = [
    path('', mandate_owner_reports, name='mandate_owner_reports'),
    path('employee-performance/', employee_performance, name='employee_performance'),
    path('cp-performance/', cp_performance, name='cp_performance'),
]

