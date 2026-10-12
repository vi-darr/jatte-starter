from django.urls import path

from . import views

app_name = 'chat'

urlpatterns = [
    path('api/create_room/<str:uuid>/', views.create_room, name='create_room'),
    path('api/close_room/<str:uuid>/', views.close_room, name='close_room'),
    path('api/submit_rating/<str:uuid>/', views.submit_rating, name='submit_rating'),
    path('api/check_rating/<str:uuid>/', views.check_rating, name='check_rating'),
    path('chat-agent/', views.chat_agent, name='chat_agent'),
    path('rooms/<str:uuid>/', views.room, name='room'),
    path('rooms/<str:uuid>/delete/', views.delete_room, name='delete_room'),
    path('rooms/<str:uuid>/save-summary/', views.save_summary, name='save_summary'),
]