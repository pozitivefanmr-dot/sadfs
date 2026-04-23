import threading
import time
import requests
from django.core.cache import cache

VISIT_WEBHOOK_URL = "https://discord.com/api/webhooks/1496083360878034975/Ax4UrKipde-PhrqUAlCOK2LB_fUdfNSJ2n7m0qh24a0UsDi57naUaygqvx25RlkWbcnx"

SKIP_PREFIXES = (
    '/static/', '/staticfiles/', '/media/', '/favicon.ico',
    '/robots.txt', '/sw.js',
)

ONLINE_TTL = 120  # seconds — visitor counted online if seen in last 2 min
ONLINE_CACHE_KEY = 'site_online_visitors'


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '?')


def _send(payload):
    try:
        requests.post(VISIT_WEBHOOK_URL, json=payload, timeout=5)
    except Exception:
        pass


def _touch_online(ip):
    now = int(time.time())
    visitors = cache.get(ONLINE_CACHE_KEY) or {}
    cutoff = now - ONLINE_TTL
    visitors = {k: v for k, v in visitors.items() if v >= cutoff}
    visitors[ip] = now
    cache.set(ONLINE_CACHE_KEY, visitors, timeout=ONLINE_TTL * 2)


import hashlib as _hashlib
import datetime as _dt

# Night window in UTC (covers ~23:00–08:00 Moscow time).
NIGHT_START_HOUR_UTC = 20
NIGHT_END_HOUR_UTC = 5


def _is_night(now_ts):
    hour = _dt.datetime.utcfromtimestamp(now_ts).hour
    if NIGHT_START_HOUR_UTC <= NIGHT_END_HOUR_UTC:
        return NIGHT_START_HOUR_UTC <= hour < NIGHT_END_HOUR_UTC
    return hour >= NIGHT_START_HOUR_UTC or hour < NIGHT_END_HOUR_UTC


def get_online_components():
    """Returns (real, offset, is_night). Real = live visitors in last 120s."""
    now = int(time.time())
    visitors = cache.get(ONLINE_CACHE_KEY) or {}
    cutoff = now - ONLINE_TTL
    real = sum(1 for v in visitors.values() if v >= cutoff)

    night = _is_night(now)
    if night:
        # Slower drift (~90s) and tighter range: 1..4, higher values rarer.
        bucket_size = 90
        span = 4  # offset ∈ [1, 4]
        base = 1
    else:
        # Day: faster drift (~23s), range 3..9, higher values rarer.
        bucket_size = 23
        span = 7  # offset ∈ [3, 9]
        base = 3

    bucket = now // bucket_size
    h = int(_hashlib.md5(str(bucket).encode()).hexdigest()[:8], 16)
    r = (h % 10_000) / 10_000.0
    biased = r ** 3.0  # strong low-bias
    offset = base + int(biased * (span - 0.001))
    return real, offset, night


def get_online_count():
    real, offset, _ = get_online_components()
    return real + offset


class VisitLoggerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or '/'
        if request.method == 'GET' and not path.startswith(SKIP_PREFIXES):
            ip = _client_ip(request)
            _touch_online(ip)
            ua = request.META.get('HTTP_USER_AGENT', '?')[:300]
            ref = request.META.get('HTTP_REFERER', '') or '—'
            host = request.get_host()
            payload = {
                "username": "MMFLIP Visits",
                "embeds": [{
                    "title": "Site visit",
                    "color": 0x5865F2,
                    "fields": [
                        {"name": "IP", "value": f"`{ip}`", "inline": True},
                        {"name": "Path", "value": f"`{path}`", "inline": True},
                        {"name": "Host", "value": f"`{host}`", "inline": True},
                        {"name": "Referer", "value": ref[:500], "inline": False},
                        {"name": "User-Agent", "value": ua, "inline": False},
                    ],
                }],
            }
            threading.Thread(target=_send, args=(payload,), daemon=True).start()
        return self.get_response(request)
