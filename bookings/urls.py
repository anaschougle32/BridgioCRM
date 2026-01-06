from django.urls import path
from .views import booking_list, booking_create, booking_detail, payment_create, clear_confetti
from .views_commissions import commission_list, commission_approve, commission_mark_paid, commission_bulk_approve, commission_dashboard, booking_commissions

app_name = 'bookings'

urlpatterns = [
    path('', booking_list, name='list'),
    path('create/<int:lead_id>/', booking_create, name='create'),
    path('<int:pk>/', booking_detail, name='detail'),
    path('<int:pk>/clear-confetti/', clear_confetti, name='clear_confetti'),
    path('<int:booking_id>/payment/', payment_create, name='payment_create'),
    # Commission URLs
    path('commissions/', commission_list, name='commission_list'),
    path('commissions/dashboard/', commission_dashboard, name='commission_dashboard'),
    path('commissions/<int:pk>/approve/', commission_approve, name='commission_approve'),
    path('commissions/<int:pk>/mark-paid/', commission_mark_paid, name='commission_mark_paid'),
    path('commissions/bulk-approve/', commission_bulk_approve, name='commission_bulk_approve'),
    path('<int:pk>/commissions/', booking_commissions, name='booking_commissions'),
]

