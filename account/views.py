from django.shortcuts import render

from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from django.conf import settings


def logout_view(request):
    """Log out the current user and redirect to the landing page."""
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "You have been logged out.")
    return redirect(settings.LOGOUT_REDIRECT_URL or '/login/')