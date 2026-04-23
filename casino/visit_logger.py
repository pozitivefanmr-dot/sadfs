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


def get_online_count():
    """Real online count + drifting fake offset, mostly [3,4], rarely up to 9."""
    import hashlib
    now = int(time.time())
    visitors = cache.get(ONLINE_CACHE_KEY) or {}
    cutoff = now - ONLINE_TTL
    real = sum(1 for v in visitors.values() if v >= cutoff)
    # New bucket every ~23s; biased toward low values (3-4),
    # rarely climbs near 9. Deterministic per-bucket via md5.
    bucket = now // 23
    h = int(hashlib.md5(str(bucket).encode()).hexdigest()[:8], 16)
    r = (h % 10_000) / 10_000.0  # 0..1
    # Strong low-bias: r ** 3 keeps most samples near 0
    biased = r ** 3
    offset = 3 + int(biased * 6.999)  # 3..9, ~9 very rare
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
