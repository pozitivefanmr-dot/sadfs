import os
from django.contrib import admin
from django.http import Http404
from django.urls import path, include, re_path
from django_otp.admin import OTPAdminSite

admin.site.__class__ = OTPAdminSite

ADMIN_URL_PATH = os.environ.get('ADMIN_URL_PATH', '').strip().strip('/')


def _admin_decoy(request, *args, **kwargs):
    raise Http404


urlpatterns = [
    re_path(r'^admin(?:/.*)?$', _admin_decoy),
]

if ADMIN_URL_PATH and ADMIN_URL_PATH != 'admin':
    urlpatterns.append(path(f'{ADMIN_URL_PATH}/', admin.site.urls))

urlpatterns.append(path('', include('casino.urls')))
