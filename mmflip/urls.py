import os
from django.contrib import admin
from django.http import Http404
from django.urls import path, include, re_path
from django_otp.admin import OTPAdminSite

# Подменяем стандартную админку на OTP-защищённую:
# вход без подтверждённого TOTP-устройства невозможен.
admin.site.__class__ = OTPAdminSite

# Секретный путь для админки. Задай в env: ADMIN_URL_PATH=my-super-secret-xyz
# Без завершающего слеша. Если переменная не задана — админка НЕ монтируется вовсе.
ADMIN_URL_PATH = os.environ.get('ADMIN_URL_PATH', '').strip().strip('/')


def _admin_decoy(request, *args, **kwargs):
    """Приманка: /admin/ и любые его подпути отвечают 404,
    как будто никакой админки на сайте нет."""
    raise Http404


urlpatterns = [
    # Приманка — стандартный путь /admin/ всегда 404.
    re_path(r'^admin(?:/.*)?$', _admin_decoy),
]

# Реальная админка — только если задан секретный путь в env.
if ADMIN_URL_PATH and ADMIN_URL_PATH != 'admin':
    urlpatterns.append(path(f'{ADMIN_URL_PATH}/', admin.site.urls))

urlpatterns.append(path('', include('casino.urls')))
