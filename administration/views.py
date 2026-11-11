from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth.models import Group
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from account.models import User
from account.forms import AddUserForm, EditUserForm
from account.utils import get_active_user_ids, get_user_online_status
from chat.models import Room, ServiceRating, ConvoSummary
 
from datetime import datetime
from django.conf import settings as conf 

def _get_period_range(period):
    """Return (start, end) datetimes for the given filter period."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == 'week':
        start = today_start - timedelta(days=today_start.weekday())  # Monday
    elif period == 'month':
        start = today_start.replace(day=1)
    else:  # 'today' or default
        start = today_start

    return start, now


def _get_active_agents_count():
    """Count staff users whose session is genuinely active."""
    user_ids = get_active_user_ids()
    if not user_ids:
        return 0
    return User.objects.filter(pk__in=user_ids, is_staff=True).count()


@login_required
def dashboard(request):
    """Administration dashboard showing high-level metrics."""
    users = User.objects.filter(is_staff=True)
    period = request.GET.get('period', 'today')
    start, end = _get_period_range(period)

    # Room stats filtered by period
    rooms_in_period = Room.objects.filter(created_at__gte=start, created_at__lte=end)
    total_rooms = rooms_in_period.count()
    active_rooms = rooms_in_period.filter(status=Room.ACTIVE).count()
    waiting_rooms = rooms_in_period.filter(status=Room.WAITING).count()
    closed_rooms = rooms_in_period.filter(status=Room.CLOSED).count()

    total_agents = User.objects.filter(is_staff=True).count()
    active_agents = _get_active_agents_count()

    # Paginated room list (unfiltered – shows all rooms)
    filtered_rooms = rooms_in_period.select_related('agent', 'rating').prefetch_related('summaries__agent')
    paginator = Paginator(filtered_rooms, 20)
    page_number = request.GET.get('page')
    rooms_page = paginator.get_page(page_number)

    # Ratings filtered by period
    ratings_in_period = ServiceRating.objects.filter(created_at__gte=start, created_at__lte=end)
    rating_agg = ratings_in_period.aggregate(
        avg_overall=Avg('overall_rating'),
        avg_responsiveness=Avg('responsiveness'),
        avg_helpfulness=Avg('helpfulness'),
        count=Count('id'),
    )


    return render(request, 'dashboard.html', {
        'users': users,
        'rooms': rooms_page,
        'current_period': period,
        'total_rooms': total_rooms,
        'active_rooms': active_rooms,
        'waiting_rooms': waiting_rooms,
        'closed_rooms': closed_rooms,
        'total_agents': total_agents,
        'active_agents': active_agents,
        'rating_agg': rating_agg,
    })


@login_required
def dashboard_stats(request):
    """Return room and rating stats as JSON for a given period (AJAX)."""
    period = request.GET.get('period', 'today')
    start, end = _get_period_range(period)

    rooms_in_period = Room.objects.filter(created_at__gte=start, created_at__lte=end)

    ratings_in_period = ServiceRating.objects.filter(created_at__gte=start, created_at__lte=end)
    rating_agg = ratings_in_period.aggregate(
        avg_overall=Avg('overall_rating'),
        avg_responsiveness=Avg('responsiveness'),
        avg_helpfulness=Avg('helpfulness'),
        count=Count('id'),
    )

    return JsonResponse({
        'total_rooms': rooms_in_period.count(),
        'active_rooms': rooms_in_period.filter(status=Room.ACTIVE).count(),
        'waiting_rooms': rooms_in_period.filter(status=Room.WAITING).count(),
        'closed_rooms': rooms_in_period.filter(status=Room.CLOSED).count(),
        'active_agents': _get_active_agents_count(),
        'avg_overall': rating_agg['avg_overall'],
        'avg_responsiveness': rating_agg['avg_responsiveness'],
        'avg_helpfulness': rating_agg['avg_helpfulness'],
        'total_ratings': rating_agg['count'],
    })

@login_required
def room_list_partial(request):
    """Return only the room list partial HTML for AJAX pagination.

    Supports two filtering modes:
    - period-based: ?period=today|week|month (used by dashboard)
    - date/agent-based: ?date_from=&date_to=&agent= (used by all rooms page)
    """
    rooms = Room.objects.select_related('agent', 'rating').prefetch_related('summaries__agent')

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    agent_id = request.GET.get('agent')

    if 'date_from' in request.GET or 'date_to' in request.GET or 'agent' in request.GET:
        # Date/agent filter mode (all rooms page)
        if date_from:
            rooms = rooms.filter(created_at__date__gte=date_from)
        if date_to:
            rooms = rooms.filter(created_at__date__lte=date_to)
        if agent_id:
            rooms = rooms.filter(agent_id=agent_id)
    else:
        # Period filter mode (dashboard)
        period = request.GET.get('period', 'today')
        start, end = _get_period_range(period)
        rooms = rooms.filter(created_at__gte=start, created_at__lte=end)

    paginator = Paginator(rooms, 20)
    page_number = request.GET.get('page')
    rooms_page = paginator.get_page(page_number)

    return render(request, 'partials/recordlist.html', {
        'rooms': rooms_page,
    })


@login_required
def all_rooms(request):
    """Full page listing all rooms with date and agent filters."""
    rooms = Room.objects.select_related('agent', 'rating').prefetch_related('summaries__agent').all()

    # Apply filters if provided (for initial server-rendered load)
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    agent_id = request.GET.get('agent')

    if date_from:
        rooms = rooms.filter(created_at__date__gte=date_from)
    if date_to:
        rooms = rooms.filter(created_at__date__lte=date_to)
    if agent_id:
        rooms = rooms.filter(agent_id=agent_id)

    paginator = Paginator(rooms, 20)
    page_number = request.GET.get('page')
    rooms_page = paginator.get_page(page_number)

    agents = User.objects.filter(is_staff=True).order_by('name')

    return render(request, 'reports/all_rooms.html', {
        'rooms': rooms_page,
        'agents': agents,
        'current_date_from': date_from or '',
        'current_date_to': date_to or '',
        'current_agent': agent_id or '',
    })


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
                    user.is_superuser = True
                    user.save()
                    group = Group.objects.get(name='Managers')
                    group.user_set.add(user)
                else:
                    user.is_superuser = False
                    user.save()
                    group = Group.objects.get(name='Agents')
                    group.user_set.add(user)

                messages.success(request, 'User added successfully.')

                return redirect('administration:dashboard')
        else:
            form = AddUserForm()

        return render(request, 'staff/add_user.html', {
            'form': form
        })
    else:
        messages.error(request, 'You do not have permission to add users.')

        return redirect('administration:dashboard')


@login_required
def user_details(request, uuid):
    user = User.objects.get(pk=uuid)

    # ── Online / last-active status ──
    is_online, last_active = get_user_online_status(user)

    now = timezone.now()

    # ── Period filter for rooms & summaries ──
    period = request.GET.get('period', 'today')
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == 'week':
        period_start = today_start - timedelta(days=today_start.weekday())
    elif period == 'month':
        period_start = today_start.replace(day=1)
    else:
        period_start = today_start

    rooms_in_period = Room.objects.filter(
        agent=user, created_at__gte=period_start, created_at__lte=now,
    )
    rooms_handled_count = rooms_in_period.count()
    summaries_written_count = ConvoSummary.objects.filter(
        agent=user, created_at__gte=period_start, created_at__lte=now,
    ).count()

     # ── Paginated room list (filtered by period) ──
    filtered_rooms = rooms_in_period.select_related(
        'agent', 'rating',
    ).prefetch_related('summaries__agent')
    paginator = Paginator(filtered_rooms, 20)
    page_number = request.GET.get('page')
    rooms_page = paginator.get_page(page_number)

    # ── Ratings (not filterable — always all-time) ──
    agent_ratings = ServiceRating.objects.filter(agent=user)
    total_ratings = agent_ratings.count()

    if total_ratings > 0:
        averages = agent_ratings.aggregate(
            avg_overall=Avg('overall_rating'),
            avg_responsiveness=Avg('responsiveness'),
            avg_helpfulness=Avg('helpfulness'),
        )
    else:
        averages = {}

    recent_ratings = agent_ratings[:5]

    return render(request, 'staff/user_details.html', {
        'user': user,
        'is_online': is_online,
        'last_active': last_active,
        'rooms': rooms_page,
        'current_period': period,
        'rooms_handled_count': rooms_handled_count,
        'summaries_written_count': summaries_written_count,
        'total_ratings': total_ratings,
        'averages': averages,
        'recent_ratings': recent_ratings,
    })

@login_required
def user_ratings(request, uuid):
    user = User.objects.get(pk=uuid)

    agent_ratings = ServiceRating.objects.filter(agent=user)
    total_ratings = agent_ratings.count()
    
    if total_ratings > 0:
        averages = agent_ratings.aggregate(
            avg_overall=Avg('overall_rating'),
            avg_responsiveness=Avg('responsiveness'),
            avg_helpfulness=Avg('helpfulness'),
        )
    else:
        averages = {}

    paginator = Paginator(agent_ratings, 10)
    page_number = request.GET.get('page')
    rooms_page = paginator.get_page(page_number)

    return render(request, 'staff/user_ratings.html', {
        'user': user,
        'ratings': agent_ratings,
        'total_ratings': total_ratings,
        'averages': averages,
        'rooms': rooms_page,
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

                return redirect('administration:dashboard')
        else:
            form = EditUserForm(instance=user)

        return render(request, 'staff/edit_user.html', {
            'user': user,
            'form': form,
        })
    else:
        messages.error(request, 'You do not have permission to edit users.')

        return redirect('administration:dashboard')


@login_required
def user_dashboard(request):
    user = User.objects.get(pk=request.user.pk)

    # ── Online / last-active status ──
    is_online, last_active = get_user_online_status(user)

    now = timezone.now()

    # ── Period filter for rooms & summaries ──
    period = request.GET.get('period', 'today')
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == 'week':
        period_start = today_start - timedelta(days=today_start.weekday())
    elif period == 'month':
        period_start = today_start.replace(day=1)
    else:
        period_start = today_start

    rooms_in_period = Room.objects.filter(
        agent=user, created_at__gte=period_start, created_at__lte=now,
    )
    rooms_handled_count = rooms_in_period.count()
    summaries_written_count = ConvoSummary.objects.filter(
        agent=user, created_at__gte=period_start, created_at__lte=now,
    ).count()

     # ── Paginated room list (filtered by period) ──
    filtered_rooms = rooms_in_period.filter(status__in=[Room.CLOSED, Room.ACTIVE]).order_by('-created_at')
    paginator = Paginator(filtered_rooms, 20)
    page_number = request.GET.get('page')
    rooms_page = paginator.get_page(page_number)

    # ── Ratings (not filterable — always all-time) ──
    agent_ratings = ServiceRating.objects.filter(agent=user)
    total_ratings = agent_ratings.count()

    if total_ratings > 0:
        averages = agent_ratings.aggregate(
            avg_overall=Avg('overall_rating'),
            avg_responsiveness=Avg('responsiveness'),
            avg_helpfulness=Avg('helpfulness'),
        )
    else:
        averages = {}

    recent_ratings = agent_ratings[:10]

    return render(request, 'staff/user_dashboard.html', {
        'user': user,
        'is_online': is_online,
        'last_active': last_active,
        'rooms': rooms_page,
        'current_period': period,
        'rooms_handled_count': rooms_handled_count,
        'summaries_written_count': summaries_written_count,
        'total_ratings': total_ratings,
        'averages': averages,
        'recent_ratings': recent_ratings,
    })