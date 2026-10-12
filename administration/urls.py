from django.urls import path

from . import views

app_name = 'administration'

urlpatterns = [
    path('administration/api/stats/', views.dashboard_stats, name='dashboard_stats'),
    path('administration/rooms-partial/', views.room_list_partial, name='room_list_partial'),
    path('admin-dashboard/', views.dashboard, name='dashboard'),
    path('all-rooms/', views.all_rooms, name='all_rooms'),
    path('add-user/', views.add_user, name='add_user'),
    path('user/<uuid:uuid>/', views.user_details, name='user_details'),
    path('user-dashboard/', views.user_dashboard, name='user_dashboard'),
    path('user/<uuid:uuid>/ratings/', views.user_ratings, name='user_ratings'),
    path('user/<uuid:uuid>/edit/', views.edit_user, name='edit_user'),
]
