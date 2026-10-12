from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def index(request):
    return render(request, 'core/index.html')

@ensure_csrf_cookie
def about(request):
    return render(request, 'core/about.html')

@ensure_csrf_cookie
def services(request):
    return render(request, 'core/services.html')


@ensure_csrf_cookie
def service_website_building(request):
    return render(request, 'core/service_website_building.html')


@ensure_csrf_cookie
def service_hosting(request):
    return render(request, 'core/service_hosting.html')


@ensure_csrf_cookie
def service_webapp_development(request):
    return render(request, 'core/service_webapp_development.html')


@ensure_csrf_cookie
def service_remote_desktop(request):
    return render(request, 'core/service_remote_desktop.html')


@ensure_csrf_cookie
def service_troubleshooting(request):
    return render(request, 'core/service_troubleshooting.html')