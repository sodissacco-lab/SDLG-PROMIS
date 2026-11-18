from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import PasswordResetForm
from django.template import loader
from django.urls import reverse_lazy
from django.utils import timezone

from .auth_models import LoginThrottle
from .mailer import send_email

# 5 wrong passwords for one username, or 25 from one address, within 15 minutes
# locks that username / address for 15 minutes.
LIMITS = {"u": 5, "ip": 25}
WINDOW = timedelta(minutes=15)
LOCK = timedelta(minutes=15)


def _client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (fwd.split(",")[0].strip() or request.META.get("REMOTE_ADDR", "") or "unknown")[:80]


def _keys(request, username):
    keys = ["ip:" + _client_ip(request)]
    if username:
        keys.append("u:" + username.strip().lower()[:100])
    return keys


def _minutes_locked(keys):
    now = timezone.now()
    worst = None
    for row in LoginThrottle.objects.filter(key__in=keys, locked_until__gt=now):
        left = row.locked_until - now
        worst = left if worst is None or left > worst else worst
    if worst is None:
        return 0
    return max(1, int(worst.total_seconds() // 60) + 1)


def _register_failure(keys):
    now = timezone.now()
    for key in keys:
        row, _ = LoginThrottle.objects.get_or_create(key=key, defaults={"window_start": now})
        if now - row.window_start > WINDOW:
            row.fails, row.window_start, row.locked_until = 0, now, None
        row.fails += 1
        if row.fails >= LIMITS[key.split(":", 1)[0]]:
            row.locked_until = now + LOCK
            row.fails = 0
            row.window_start = now
        row.save()


def _clear(keys):
    LoginThrottle.objects.filter(key__in=[k for k in keys if k.startswith("u:")]).delete()


class ThrottledLoginView(auth_views.LoginView):
    template_name = "registration/login.html"

    def post(self, request, *args, **kwargs):
        keys = _keys(request, request.POST.get("username", ""))
        mins = _minutes_locked(keys)
        if mins:
            return self.render_to_response(
                self.get_context_data(
                    form=self.get_form(),
                    lock_message="Too many wrong attempts. Please wait %d minute%s and try again, "
                    "or use Forgot password." % (mins, "" if mins == 1 else "s"),
                )
            )
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        _clear(_keys(self.request, self.request.POST.get("username", "")))
        return super().form_valid(form)

    def form_invalid(self, form):
        _register_failure(_keys(self.request, self.request.POST.get("username", "")))
        return super().form_invalid(form)


# ------------------------------------------------------------ forgot password
class ResetForm(PasswordResetForm):
    """Sends the reset link through the email service instead of Django's SMTP."""

    def send_mail(self, subject_template_name, email_template_name, context,
                  from_email, to_email, html_email_template_name=None):
        subject = "".join(loader.render_to_string(subject_template_name, context).splitlines())
        body = loader.render_to_string(email_template_name, context)
        send_email(to_email, subject, body)


class ForgotPasswordView(auth_views.PasswordResetView):
    template_name = "core/auth_form.html"
    form_class = ResetForm
    email_template_name = "core/password_reset_email.txt"
    subject_template_name = "core/password_reset_subject.txt"
    success_url = reverse_lazy("forgot_password_done")
    extra_context = {
        "title": "Forgot your password?",
        "intro": "Enter the email address on your account. We will send you a link to choose a new password.",
        "button": "Send reset link",
    }


class ForgotPasswordDoneView(auth_views.PasswordResetDoneView):
    template_name = "core/auth_message.html"
    extra_context = {
        "title": "Check your email",
        "message": "If that email address belongs to an account, a reset link has been sent. "
        "It can take a few minutes. If you have no email on your account, ask the system "
        "administrator to reset your password.",
    }


class ResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "core/auth_form.html"
    success_url = reverse_lazy("reset_complete")
    extra_context = {"title": "Choose a new password", "intro": "", "button": "Save new password"}


class ResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "core/auth_message.html"
    extra_context = {"title": "Password changed", "message": "Your password has been changed.", "show_login": True}


# ------------------------------------------------------------ change password
class ChangePasswordView(auth_views.PasswordChangeView):
    template_name = "core/password_change.html"
    success_url = reverse_lazy("dashboard")

    def form_valid(self, form):
        messages.success(self.request, "Your password has been changed.")
        return super().form_valid(form)
