from django.urls import path
from .views import booking_list, booking_detail, booking_create, payment_create, clear_confetti

app_name = 'bookings'

urlpatterns = [
    path('', booking_list, name='list'),
    path('create/<int:lead_id>/', booking_create, name='create'),
    path('<int:pk>/', booking_detail, name='detail'),
    path('<int:booking_id>/payment/', payment_create, name='payment_create'),
    path('<int:pk>/clear-confetti/', clear_confetti, name='clear_confetti'),
]

