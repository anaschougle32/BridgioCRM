from django.urls import path
from .views import (
    lead_list, lead_create, lead_pretag, lead_detail, send_otp, verify_otp, 
    upcoming_visits, log_call, create_reminder, complete_reminder, whatsapp, 
    lead_assign, lead_upload, lead_assign_admin, update_status
)

app_name = 'leads'

urlpatterns = [
    path('', lead_list, name='list'),
    path('create/', lead_create, name='create'),
    path('pretag/', lead_pretag, name='pretag'),
    path('upload/', lead_upload, name='upload'),
    path('assign/', lead_assign, name='assign'),
    path('assign-admin/', lead_assign_admin, name='assign_admin'),
    path('upcoming-visits/', upcoming_visits, name='upcoming_visits'),
    path('<int:pk>/', lead_detail, name='detail'),
    path('<int:pk>/send-otp/', send_otp, name='send_otp'),
    path('<int:pk>/verify-otp/', verify_otp, name='verify_otp'),
    path('<int:pk>/update-status/', update_status, name='update_status'),
    path('<int:pk>/log-call/', log_call, name='log_call'),
    path('<int:pk>/create-reminder/', create_reminder, name='create_reminder'),
    path('<int:pk>/complete-reminder/<int:reminder_id>/', complete_reminder, name='complete_reminder'),
    path('<int:pk>/whatsapp/', whatsapp, name='whatsapp'),
]


