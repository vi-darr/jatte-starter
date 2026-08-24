from django.urls import path

from . import views

urlpatterns = [
    path('api/create_room/<str:uuid>/', views.create_room, name='create_room'),
]