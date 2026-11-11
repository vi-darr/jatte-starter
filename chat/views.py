import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.contrib import messages

from .models import Room, ConvoSummary, ServiceRating
from .forms import ConvoSummaryForm, ServiceRatingForm

@require_POST
def create_room(request, uuid):
    name = request.POST.get('name', '')
    url = request.POST.get('url', '')

    room, created = Room.objects.get_or_create(
        uuid=uuid,
        defaults={'client': name, 'url': url}
    )

    # If reconnecting to an existing room, reopen it
    if not created and room.status == Room.CLOSED:
        room.status = Room.WAITING
        room.save()

    return JsonResponse({'message': 'room created' if created else 'room exists'})

@require_POST
def close_room(request, uuid):
    try:
        room = Room.objects.get(uuid=uuid)
        room.status = Room.CLOSED
        room.save()
        
        # Notify connected WebSocket clients that the room is closed
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{uuid}',
            {'type': 'room_closed'}
        )

        return JsonResponse({'message': 'room closed'})
    except Room.DoesNotExist:
        return JsonResponse({'message': 'room not found'}, status=404)


@login_required
def chat_agent(request):
    rooms =Room.objects.filter(status__in=[Room.WAITING, Room.ACTIVE]).order_by('-created_at')
    paginator = Paginator(rooms, 20)
    page_number = request.GET.get('page')
    rooms_page = paginator.get_page(page_number)

    return render(request, 'chat/chat_agent.html', {
        'rooms': rooms_page,
    })

@login_required
def room(request, uuid):
    room = Room.objects.get(uuid=uuid)

    if room.status == Room.WAITING:
        room.status = Room.ACTIVE
        room.agent = request.user
        room.save()

    # Load current agent's own summary (if any)
    try:
        my_summary = ConvoSummary.objects.get(room=room, agent=request.user)
    except ConvoSummary.DoesNotExist:
        my_summary = None

    summary_form = ConvoSummaryForm(instance=my_summary)

    # Summaries written by other agents for this room
    other_summaries = ConvoSummary.objects.filter(room=room).exclude(agent=request.user)

    return render(request, 'chat/room.html', {
        'room': room,
        'summary_form': summary_form,
        'other_summaries': other_summaries,
    })

@login_required
def delete_room(request, uuid):
    if request.user.has_perm('room.delete_room'):
        room = Room.objects.get(uuid=uuid)
        if room.status != Room.CLOSED:
            messages.error(request, 'Cannot delete an active room.')
            return redirect('chat:chat-agent')
        else:
            room.delete()

        messages.success(request, 'Room deleted.')
        
        return redirect('chat:chat-agent')
    else:
        messages.error(request, 'You do not have permission to delete rooms.')
        
        return redirect('chat:chat-agent')

@login_required
@require_POST
def save_summary(request, uuid):
    room_obj = Room.objects.get(uuid=uuid)

    # Get or create the summary for the current agent only
    try:
        summary_instance = ConvoSummary.objects.get(room=room_obj, agent=request.user)
    except ConvoSummary.DoesNotExist:
        summary_instance = None

    form = ConvoSummaryForm(request.POST, instance=summary_instance)

    if form.is_valid():
        summary = form.save(commit=False)
        summary.room = room_obj
        summary.agent = request.user
        summary.client_name = room_obj.client
        summary.save()

        messages.success(request, 'Conversation summary saved.')
    else:
        messages.error(request, 'Error saving summary.')

    return redirect('chat:room', uuid=uuid)

@require_POST
def submit_rating(request, uuid):
    """Client submits a service rating after conversation closes."""
    try:
        room = Room.objects.get(uuid=uuid)
    except Room.DoesNotExist:
        return JsonResponse({'error': 'Room not found'}, status=404)

    if hasattr(room, 'rating'):
        return JsonResponse({'error': 'Rating already submitted'}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    overall = data.get('overall_rating')
    if not overall or not (1 <= int(overall) <= 5):
        return JsonResponse({'error': 'overall_rating is required (1-5)'}, status=400)

    rating = ServiceRating.objects.create(
        room=room,
        agent=room.agent,
        client_name=room.client,
        overall_rating=int(overall),
        responsiveness=data.get('responsiveness') or None,
        helpfulness=data.get('helpfulness') or None,
        comment=data.get('comment', ''),
    )

    return JsonResponse({'message': 'Rating submitted', 'id': str(rating.id)})


def check_rating(request, uuid):
    """Check if a room already has a rating."""
    try:
        room = Room.objects.get(uuid=uuid)
    except Room.DoesNotExist:
        return JsonResponse({'error': 'Room not found'}, status=404)

    has_rating = hasattr(room, 'rating')
    return JsonResponse({'has_rating': has_rating})