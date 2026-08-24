import json
from django.http import JsonResponse
from django.views.decorators.http import require_post

from .models import Room, Message

@require_post
def create_room(request, uuid):
    name = request.POST.get('name', '')
    url = request.POST.get('url', '')

    Room.objects.create(uuid=uuid, client=name, url=url)

    return JsonResponse({'message': 'room created'})