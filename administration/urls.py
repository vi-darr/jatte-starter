from django.urls import path

from . import views

app_name = 'administration'

urlpatterns = [
    path('administration/api/stats/', views.dashboard_stats, name='dashboard_stats'),
    path('administration/rooms-partial/', views.room_list_partial, name='room_list_partial'),
    path('administration/reports/', views.report_list, name='report_list'),
    path('administration/', views.dashboard, name='dashboard'),
    path('administration/rooms/', views.all_rooms, name='all_rooms'),
    path('administration/add-user/', views.add_user, name='add_user'),
    path('administration/user/<uuid:uuid>/', views.user_details, name='user_details'),
    path('administration/user/<uuid:uuid>/edit/', views.edit_user, name='edit_user'),
    path('administration/reports/generate/', views.generate_report, name='generate_report'),
    path('administration/reports/<uuid:pk>/', views.report_detail, name='report_detail'),
    path('administration/reports/<uuid:pk>/delete/', views.delete_report, name='delete_report'),
]
