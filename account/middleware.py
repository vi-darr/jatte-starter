from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone

from datetime import datetime


class SessionTimeoutMiddleware:
    """Enforce idle and absolute session timeouts for authenticated users.

    - Idle timeout: session expires after SESSION_IDLE_TIMEOUT seconds of
      inactivity (no requests).
    - Absolute timeout: session expires after SESSION_ABSOLUTE_TIMEOUT seconds
      since login, regardless of activity.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def _save_last_active(self, request, last_activity):
        """Persist last_active_at on the User model before flushing the session."""
        request.user.last_active_at = last_activity
        request.user.save(update_fields=['last_active_at'])

    def __call__(self, request):
        # Only enforce timeouts on authenticated users
        if request.user.is_authenticated:
            # Don't intercept the login page itself (would cause a redirect loop)
            login_url = getattr(settings, 'LOGIN_URL', '/login/')
            if request.path == login_url:
                return self.get_response(request)

            now = timezone.now()

            login_time_str = request.session.get('login_time')
            last_activity_str = request.session.get('last_activity')

            # If timestamps are missing (e.g. session created before middleware
            # was installed), stamp them now rather than locking the user out.
            if not login_time_str or not last_activity_str:
                request.session['login_time'] = now.isoformat()
                request.session['last_activity'] = now.isoformat()
                return self.get_response(request)

            login_time = datetime.fromisoformat(login_time_str)
            last_activity = datetime.fromisoformat(last_activity_str)

            # Make datetimes timezone-aware if they aren't already
            if timezone.is_naive(login_time):
                login_time = timezone.make_aware(login_time)
            if timezone.is_naive(last_activity):
                last_activity = timezone.make_aware(last_activity)

            absolute_timeout = getattr(settings, 'SESSION_ABSOLUTE_TIMEOUT', 28800)
            idle_timeout = getattr(settings, 'SESSION_IDLE_TIMEOUT', 1800)

            # Check absolute timeout (8 hours since login)
            if (now - login_time).total_seconds() > absolute_timeout:
                self._save_last_active(request, last_activity)
                request.session.flush()
                return redirect(f'{login_url}?reason=expired')

            # Check idle timeout (30 minutes since last activity)
            if (now - last_activity).total_seconds() > idle_timeout:
                self._save_last_active(request, last_activity)
                request.session.flush()
                return redirect(f'{login_url}?reason=idle')

            # Session is valid — update last activity timestamp
            request.session['last_activity'] = now.isoformat()

        return self.get_response(request)
