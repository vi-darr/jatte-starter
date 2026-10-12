from django.urls import path

from . import views

app_name = 'core'


urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('services/website-building/', views.service_website_building, name='service_website_building'),
    path('services/hosting/', views.service_hosting, name='service_hosting'),
    path('services/webapp-development/', views.service_webapp_development, name='service_webapp_development'),
    path('services/remote-desktop-services/', views.service_remote_desktop, name='service_remote_desktop'),
    path('services/troubleshooting/', views.service_troubleshooting, name='service_troubleshooting'),
]
