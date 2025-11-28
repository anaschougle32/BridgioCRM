from django.urls import path
from .views import CustomLoginView, logout_view, user_list, user_create, user_edit, user_toggle_active

app_name = 'accounts'

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('users/', user_list, name='user_list'),
    path('users/create/', user_create, name='user_create'),
    path('users/<int:pk>/edit/', user_edit, name='user_edit'),
    path('users/<int:pk>/toggle-active/', user_toggle_active, name='user_toggle_active'),
]
