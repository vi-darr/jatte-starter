from datetime import datetime

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.utils import timezone


def stamp_login_time(sender, request, user, **kwargs):
    """Record the login timestamp in the session for timeout tracking."""
    now = timezone.now().isoformat()
    request.session['login_time'] = now
    request.session['last_activity'] = now


def save_last_active_on_logout(sender, request, user, **kwargs):
    """Persist last_active_at on the User model before the session is flushed.

    Django sends user_logged_out *before* flushing the session, so the
    session data is still available here.
    """
    last_activity_str = request.session.get('last_activity')
    if last_activity_str:
        last_activity = datetime.fromisoformat(last_activity_str)
        if timezone.is_naive(last_activity):
            last_activity = timezone.make_aware(last_activity)
        user.last_active_at = last_activity
    else:
        user.last_active_at = timezone.now()
    user.save(update_fields=['last_active_at'])


user_logged_in.connect(stamp_login_time)
user_logged_out.connect(save_last_active_on_logout)
