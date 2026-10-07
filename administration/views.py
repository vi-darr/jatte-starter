from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth.models import Group
from django.contrib.sessions.models import Session
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from chat.models import Room, Message, ServiceRating
from account.models import User
from account.forms import AddUserForm, EditUserForm

from .models import Report
from .forms import GenerateReportForm, ReportFilterForm    

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
    """Count staff users with a non-expired session (i.e. currently logged in)."""
    now = timezone.now()
    active_sessions = Session.objects.filter(expire_date__gt=now)
    user_ids = set()
    for session in active_sessions:
        data = session.get_decoded()
        uid = data.get('_auth_user_id')
        if uid:
            user_ids.add(uid)
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
    paginator = Paginator(filtered_rooms, 10)
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

    recent_reports = Report.objects.all()[:5]

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
        'recent_reports': recent_reports,
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

    paginator = Paginator(rooms, 10)
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

    paginator = Paginator(rooms, 10)
    page_number = request.GET.get('page')
    rooms_page = paginator.get_page(page_number)

    agents = User.objects.filter(is_staff=True).order_by('name')

    return render(request, 'all_rooms.html', {
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
                    group = Group.objects.get(name='Managers')
                    group.user_set.add(user)
                else:
                    group = Group.objects.get(name='Agents')
                    group.user_set.add(user)

                messages.success(request, 'User added successfully.')

                return redirect('/administration/')
        else:
            form = AddUserForm()

        return render(request, 'staff/add_user.html', {
            'form': form
        })
    else:
        messages.error(request, 'You do not have permission to add users.')

        return redirect('/administration/')


@login_required
def user_details(request, uuid):
    user = User.objects.get(pk=uuid)
    rooms = user.rooms.all().select_related('agent', 'rating').prefetch_related('summaries__agent')

    # Agent performance stats
    agent_ratings = ServiceRating.objects.filter(agent=user)
    total_ratings = agent_ratings.count()

    if total_ratings > 0:
        from django.db.models import Avg
        averages = agent_ratings.aggregate(
            avg_overall=Avg('overall_rating'),
            avg_responsiveness=Avg('responsiveness'),
            avg_helpfulness=Avg('helpfulness'),
        )
    else:
        averages = {}

    recent_ratings = agent_ratings[:10]

    return render(request, 'staff/user_details.html', {
        'user': user,
        'rooms': rooms,
        'total_ratings': total_ratings,
        'averages': averages,
        'recent_ratings': recent_ratings,
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

                return redirect('/administration/')
        else:
            form = EditUserForm(instance=user)

        return render(request, 'staff/edit_user.html', {
            'user': user,
            'form': form,
        })
    else:
        messages.error(request, 'You do not have permission to edit users.')

        return redirect('/administration/')


@login_required
def report_list(request):
    """List all generated reports with optional period filter."""
    filter_form = ReportFilterForm(request.GET)
    reports = Report.objects.all()

    if filter_form.is_valid():
        period = filter_form.cleaned_data.get('period')
        if period:
            reports = reports.filter(period=period)

    return render(request, 'reports/report_list.html', {
        'reports': reports,
        'filter_form': filter_form,
    })


@login_required
def report_detail(request, pk):
    """View a single report's details."""
    report = get_object_or_404(Report, pk=pk)
    return render(request, 'reports/report_detail.html', {
        'report': report,
    })


@login_required
def generate_report(request):
    """Generate a new report by computing metrics for the chosen period."""
    if request.method == 'POST':
        form = GenerateReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.created_by = request.user

            start = report.period_start
            end = report.period_end

            # Compute snapshot metrics for the period
            rooms_in_period = Room.objects.filter(created_at__gte=start, created_at__lte=end)
            report.total_rooms = rooms_in_period.count()
            report.active_rooms = rooms_in_period.filter(status=Room.ACTIVE).count()
            report.closed_rooms = rooms_in_period.filter(status=Room.CLOSED).count()
            report.waiting_rooms = rooms_in_period.filter(status=Room.WAITING).count()

            ratings_in_period = ServiceRating.objects.filter(
                created_at__gte=start, created_at__lte=end
            )
            report.total_ratings = ratings_in_period.count()

            agg = ratings_in_period.aggregate(
                avg_overall=Avg('overall_rating'),
                avg_responsiveness=Avg('responsiveness'),
                avg_helpfulness=Avg('helpfulness'),
            )
            report.avg_overall_rating = agg['avg_overall']
            report.avg_responsiveness = agg['avg_responsiveness']
            report.avg_helpfulness = agg['avg_helpfulness']

            report.save()

            messages.success(request, 'Report generated successfully.')
            return redirect('administration:report_detail', pk=report.pk)
    else:
        form = GenerateReportForm()

    return render(request, 'reports/generate_report.html', {
        'form': form,
    })


@login_required
def delete_report(request, pk):
    """Delete a report (POST only)."""
    report = get_object_or_404(Report, pk=pk)

    if request.method == 'POST':
        report.delete()
        messages.success(request, 'Report deleted.')
        return redirect('administration:report_list')

    return redirect('administration:report_detail', pk=pk)
