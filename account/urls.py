from django.contrib.auth import views
from django.contrib.auth.views import LoginView
from django.urls import path
from . import views

from .forms import LoginForm

app_name = 'account'


urlpatterns = [
    path('login/', LoginView.as_view(template_name='account/login.html', form_class=LoginForm), name='login'),
    path('logout/', views.logout_view, name='logout'),
]