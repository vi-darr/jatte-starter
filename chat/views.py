import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.shortcuts import render, redirect
from django.contrib import messages

from .models import Room, Message
from account.models import User
from account.forms import AddUserForm, EditUserForm

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
        return JsonResponse({'message': 'room closed'})
    except Room.DoesNotExist:
        return JsonResponse({'message': 'room not found'}, status=404)


@login_required
def admin(request):
    rooms = Room.objects.all()
    users = User.objects.filter(is_staff=True)

    return render(request, 'chat/admin.html', {
        'rooms': rooms,
        'users': users
    })

@login_required
def room(request, uuid):
    room = Room.objects.get(uuid=uuid)

    if room.status == Room.WAITING:
        room.status = Room.ACTIVE
        room.agent = request.user
        room.save()

    return render(request, 'chat/room.html', {
        'room': room
    })

@login_required
def delete_room(request, uuid):
    if request.user.has_perm('room.delete_room'):
        room = Room.objects.get(uuid=uuid)
        room.delete()

        messages.success(request, 'Room deleted.')
        
        return redirect('/chat-admin/')
    else:
        messages.error(request, 'You do not have permission to delete rooms.')
        
        return redirect('/chat-admin/')


@login_required
def add_user(request):
    if request.user.has_perm('user.add_user'):
        if request.method == 'POST':
            form = AddUserForm(request.POST)

            if form.is_valid():
                user = form.save(commit=False)
                user.is_staff = True
                user.set_password(request.POST.get('password'))
                user.save()

                if user.role == User.MANAGER:
                    group = Group.objects.get(name='Managers')
                    group.user_set.add(user)
                else:
                    group = Group.objects.get(name='Agents')
                    group.user_set.add(user)

                messages.success(request, 'User added successfully.')

                return redirect('/chat-admin/')
        else:
            form = AddUserForm()

        return render(request, 'chat/add_user.html', {
            'form': form
        })
    else:
        messages.error(request, 'You do not have permission to add users.')

        return redirect('/chat-admin/')


@login_required
def user_details(request, uuid):
    user = User.objects.get(pk=uuid)
    rooms = user.rooms.all()

    return render(request, 'chat/user_details.html', {
        'user': user,
        'rooms': rooms
    })

@login_required
def edit_user(request, uuid):
    if request.user.has_perm('user.edit_user'):
        user = User.objects.get(pk=uuid)

        if request.method == 'POST':
            form = EditUserForm(request.POST, instance=user)

            if form.is_valid():
                form.save()

                messages.success(request, 'User updated successfully.')

                return redirect('/chat-admin/')
        else:
            form = EditUserForm(instance=user)

        return render(request, 'chat/edit_user.html', {
            'user': user,
            'form': form,
        })
    else:
        messages.error(request, 'You do not have permission to edit users.')

        return redirect('/chat-admin/')
