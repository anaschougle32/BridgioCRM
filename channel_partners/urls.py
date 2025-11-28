from django.urls import path
from .views import cp_list, cp_detail

app_name = 'channel_partners'

urlpatterns = [
    path('', cp_list, name='list'),
    path('<int:pk>/', cp_detail, name='detail'),
]

