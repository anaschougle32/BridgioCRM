from django.urls import path
from .views import (
    lead_list, lead_create, lead_pretag, lead_detail, send_otp, verify_otp, 
    upcoming_visits, visits_list, pretagged_leads, schedule_visit, scheduled_visits, closing_manager_visits, log_call, create_reminder, complete_reminder, whatsapp, 
    lead_assign, lead_upload, lead_assign_admin, update_status, update_notes,
    upload_analyze, upload_preview, lead_upload_errors_csv, lead_download,
    update_budget, update_configuration, track_call_click, search_channel_partners, search_leads
)

app_name = 'leads'

urlpatterns = [
    path('', lead_list, name='list'),
    path('create/', lead_create, name='create'),
    path('pretag/', lead_pretag, name='pretag'),
    path('schedule-visit/', schedule_visit, name='schedule_visit'),
    path('scheduled-visits/', scheduled_visits, name='scheduled_visits'),
    path('upload/', lead_upload, name='upload'),
    path('upload/analyze/', upload_analyze, name='upload_analyze'),
    path('upload/preview/', upload_preview, name='upload_preview'),
    path('upload/errors/<str:session_id>/', lead_upload_errors_csv, name='upload_errors_csv'),
    path('download/', lead_download, name='download'),
    path('assign/', lead_assign, name='assign'),
    path('assign-admin/', lead_assign_admin, name='assign_admin'),
    path('upcoming-visits/', upcoming_visits, name='upcoming_visits'),
    path('visits/', visits_list, name='visits_list'),
    path('my-visits/', closing_manager_visits, name='closing_manager_visits'),
    path('pretagged-leads/', pretagged_leads, name='pretagged_leads'),
    path('scheduled-visits/', scheduled_visits, name='scheduled_visits'),
    path('<int:pk>/', lead_detail, name='detail'),
    path('<int:pk>/send-otp/', send_otp, name='send_otp'),
    path('<int:pk>/verify-otp/', verify_otp, name='verify_otp'),
    path('<int:pk>/update-status/', update_status, name='update_status'),
    path('<int:pk>/update-budget/', update_budget, name='update_budget'),
    path('<int:pk>/update-configuration/', update_configuration, name='update_configuration'),
    path('<int:pk>/log-call/', log_call, name='log_call'),
    path('<int:pk>/track-call-click/', track_call_click, name='track_call_click'),
    path('<int:pk>/create-reminder/', create_reminder, name='create_reminder'),
    path('<int:pk>/complete-reminder/<int:reminder_id>/', complete_reminder, name='complete_reminder'),
    path('<int:pk>/update-notes/', update_notes, name='update_notes'),
    path('<int:pk>/whatsapp/', whatsapp, name='whatsapp'),
    path('search-cp/', search_channel_partners, name='search_cp'),
    path('search-leads/', search_leads, name='search_leads'),
]


