from django.urls import path

from . import views

app_name = 'chat'

urlpatterns = [
    path('api/create_room/<str:uuid>/', views.create_room, name='create_room'),
    path('api/close_room/<str:uuid>/', views.close_room, name='close_room'),
    path('api/submit_rating/<str:uuid>/', views.submit_rating, name='submit_rating'),
    path('api/check_rating/<str:uuid>/', views.check_rating, name='check_rating'),
    path('chat-admin/', views.chat_admin, name='chat_admin'),
    path('chat-admin/add-user/', views.add_user, name='add_user'),
    path('chat-admin/user/<uuid:uuid>/', views.user_details, name='user_details'),
    path('chat-admin/user/<uuid:uuid>/edit/', views.edit_user, name='edit_user'),
    path('rooms/<str:uuid>/', views.room, name='room'),
    path('rooms/<str:uuid>/delete/', views.delete_room, name='delete_room'),
    path('rooms/<str:uuid>/save-summary/', views.save_summary, name='save_summary'),
]