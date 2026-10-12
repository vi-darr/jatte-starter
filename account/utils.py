from datetime import datetime

from django.conf import settings as conf
from django.contrib.sessions.models import Session
from django.utils import timezone


def _validate_session_data(data, now, idle_timeout, absolute_timeout):
    """Check a decoded session dict against idle and absolute timeouts.

    Returns (is_valid, last_activity_dt):
        is_valid       – True if the session is genuinely active
        last_activity  – timezone-aware datetime of the last request, or None
    """
    last_activity_str = data.get('last_activity')
    login_time_str = data.get('login_time')
    if not last_activity_str or not login_time_str:
        return False, None

    last_activity = datetime.fromisoformat(last_activity_str)
    login_time = datetime.fromisoformat(login_time_str)
    if timezone.is_naive(last_activity):
        last_activity = timezone.make_aware(last_activity)
    if timezone.is_naive(login_time):
        login_time = timezone.make_aware(login_time)

    idle_ok = (now - last_activity).total_seconds() <= idle_timeout
    absolute_ok = (now - login_time).total_seconds() <= absolute_timeout

    return (idle_ok and absolute_ok), last_activity


def get_user_online_status(user):
    """Return (is_online, last_active) for a single user.

    is_online   – True if the user has a session passing both timeout checks
    last_active – timezone-aware datetime of their most recent activity, or None
    """
    now = timezone.now()
    idle_timeout = getattr(conf, 'SESSION_IDLE_TIMEOUT', 1800)
    absolute_timeout = getattr(conf, 'SESSION_ABSOLUTE_TIMEOUT', 28800)

    is_online = False
    last_active = None
    user_pk_str = str(user.pk)

    for session in Session.objects.filter(expire_date__gt=now):
        data = session.get_decoded()
        if data.get('_auth_user_id') != user_pk_str:
            continue

        valid, last_activity = _validate_session_data(
            data, now, idle_timeout, absolute_timeout,
        )

        if valid:
            is_online = True
            last_active = last_activity
            break  # confirmed online
        elif last_activity is not None:
            # Expired session — track most recent activity for "last seen"
            if last_active is None or last_activity > last_active:
                last_active = last_activity

    # Fall back to the persisted timestamp when no session is found
    # (e.g. after normal logout or session expiry)
    if not is_online and last_active is None and user.last_active_at:
        last_active = user.last_active_at

    return is_online, last_active


def get_active_user_ids():
    """Return a set of user-PK strings whose sessions are genuinely active.

    A session is active when:
    1. Cookie has not expired  (expire_date > now)
    2. User was active within the idle window  (SESSION_IDLE_TIMEOUT)
    3. Session has not exceeded the absolute lifetime  (SESSION_ABSOLUTE_TIMEOUT)
    """
    now = timezone.now()
    idle_timeout = getattr(conf, 'SESSION_IDLE_TIMEOUT', 1800)
    absolute_timeout = getattr(conf, 'SESSION_ABSOLUTE_TIMEOUT', 28800)

    user_ids = set()

    for session in Session.objects.filter(expire_date__gt=now):
        data = session.get_decoded()
        uid = data.get('_auth_user_id')
        if not uid:
            continue

        valid, _ = _validate_session_data(
            data, now, idle_timeout, absolute_timeout,
        )
        if valid:
            user_ids.add(uid)

    return user_ids
