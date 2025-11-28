from django.urls import path
from .views import attendance_list, attendance_summary, attendance_checkin

app_name = 'attendance'

urlpatterns = [
    path('', attendance_list, name='list'),
    path('checkin/', attendance_checkin, name='checkin'),
    path('summary/', attendance_summary, name='summary'),
]

