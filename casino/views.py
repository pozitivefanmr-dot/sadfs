import requests
import json
import random
import secrets
import string
import hashlib
import re
import threading
import time
import logging

logger = logging.getLogger(__name__)
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.template.loader import render_to_string
from django.utils.timesince import timesince
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Q
from django.contrib.auth.models import User
from django.contrib import messages
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited
from .models import *


import os as _os
import hmac as _hmac
from urllib.parse import urlparse as _urlparse

# Виртуальный аккаунт-получатель комиссии. Не должен отображаться в лидерборде.
# Можно переопределить через env COMMISSION_OWNER.
COMMISSION_OWNER = _os.environ.get('COMMISSION_OWNER', 'house').strip() or 'house'
HIDDEN_USERNAMES = {COMMISSION_OWNER.lower(), 'admin', 'house', 'system', 'bot'}


def _bot_token_ok(request):
    """Заголовок X-Bot-Token должен совпадать с env BOT_API_TOKEN.
    Если переменная не задана — отклоняем всё (fail-closed)."""
    expected = (_os.environ.get('BOT_API_TOKEN') or '').strip()
    if not expected:
        return False
    provided = request.headers.get('X-Bot-Token', '').strip()
    return bool(provided) and _hmac.compare_digest(provided, expected)


# === IMAGE URL VALIDATION ===
ALLOWED_IMAGE_HOSTS = {
    'tr.rbxcdn.com',
    't0.rbxcdn.com', 't1.rbxcdn.com', 't2.rbxcdn.com',
    't3.rbxcdn.com', 't4.rbxcdn.com', 't5.rbxcdn.com',
    't6.rbxcdn.com', 't7.rbxcdn.com',
    'static.wikia.nocookie.net',
    'thumbs.roblox.com',
    'www.roblox.com',
    'roblox.com',
}
SAFE_IMAGE_FALLBACK = "https://static.wikia.nocookie.net/murder-mystery-2/images/5/53/Godly_Icon.png"


def safe_image_url(url):
    """Возвращает URL только если он на https и хост в whitelist. Иначе fallback."""
    if not url or not isinstance(url, str):
        return SAFE_IMAGE_FALLBACK
    url = url.strip()
    if len(url) > 500:
        return SAFE_IMAGE_FALLBACK
    try:
        parsed = _urlparse(url)
    except Exception:
        return SAFE_IMAGE_FALLBACK
    if parsed.scheme != 'https':
        return SAFE_IMAGE_FALLBACK
    host = (parsed.hostname or '').lower()
    if host not in ALLOWED_IMAGE_HOSTS:
        return SAFE_IMAGE_FALLBACK
    return url


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_item_action(username, action, item=None, *, item_id=None, item_name='', item_value=0,
                    related_game_id=None, related_giveaway_id=None, note='', request=None):
    """Создаёт запись в ItemLog. Никогда не падает — логирование не должно ломать бизнес-логику."""
    try:
        if item is not None:
            item_id = item_id or item.id
            item_name = item_name or item.item_name
            item_value = item_value or item.item_value
        ItemLog.objects.create(
            username=username or '',
            action=action,
            item_id=item_id,
            item_name=item_name or '',
            item_value=item_value or 0,
            related_game_id=related_game_id,
            related_giveaway_id=related_giveaway_id,
            note=note[:255] if note else '',
            ip_address=_client_ip(request) if request else None,
        )
    except Exception as exc:
        logger.warning("ItemLog write failed: %s", exc)


# === CHAT VALIDATION ===
CHAT_MIN_LEN = 1
CHAT_MAX_LEN = 300
CHAT_MAX_REPEAT_CHARS = 15  # запрещаем aaaaaaaaaaaaaaaa...
CHAT_RECENT_DUP_WINDOW = 60  # секунд: повторение того же сообщения от того же юзера


def validate_chat_message(user, raw_text):
    """Возвращает (cleaned_text, error_or_None)."""
    if not isinstance(raw_text, str):
        return None, "Invalid message"
    text = raw_text.strip()
    if len(text) < CHAT_MIN_LEN:
        return None, "Message is empty"
    if len(text) > CHAT_MAX_LEN:
        return None, f"Message too long (max {CHAT_MAX_LEN} chars)"

    # Запрещаем длинные подряд повторы одного символа (флуд)
    if re.search(r'(.)\1{' + str(CHAT_MAX_REPEAT_CHARS) + r',}', text):
        return None, "Please don't spam repeated characters"

    import datetime as _dt
    cutoff = timezone.now() - _dt.timedelta(seconds=CHAT_RECENT_DUP_WINDOW)
    last = ChatMessage.objects.filter(user=user).order_by('-created_at').first()
    if last and last.message.strip() == text and last.created_at >= cutoff:
        return None, "Don't repeat the same message"

    return text, None

# ==========================================
# 1. НАСТРОЙКИ И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================

# Впиши сюда реальные ники и ID твоих ботов
BOTS_CONFIG = [
    {'username': 'Bot_Trade_01', 'id': 5413661688},
    {'username': 'Bot_Trade_02', 'id': 5413661688},
]

AVATAR_CACHE = {}
AVATAR_NEGATIVE_CACHE = {}
AVATAR_NEGATIVE_TTL = 600
DEFAULT_AVATAR_URL = "https://tr.rbxcdn.com/53db0d0cb349309a7c91eb4361790e39/150/150/AvatarHeadshot/Png"
ROBLOX_API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}


# ==========================================
# DISCORD WEBHOOK — Логирование результатов игр
# ==========================================

def generate_game_hash(game_id, player1, player2, result, secret):
    """SHA-256 хеш игры для проверки честности"""
    raw = f"{game_id}:{player1}:{player2}:{result}:{secret}"
    return hashlib.sha256(raw.encode()).hexdigest()


def send_discord_game_log(game):
    """Отправляет embed с результатом игры в Discord вебхук"""
    try:
        webhook_url = getattr(settings, 'DISCORD_WEBHOOK_URL', '')
        if not webhook_url:
            logger.error("[Discord Webhook] URL пустой!")
            return

        # Время именно сыгровки (сейчас), а не создания игры
        now = timezone.now()
        played_timestamp = int(now.timestamp())

        # Предметы игроков
        p1_items = ', '.join([i.get('name', '?') for i in (game.items1 or [])])
        p2_items = ', '.join([i.get('name', '?') for i in (game.items2 or [])])
        total_value = (game.value1 or 0) + (game.value2 or 0)

        loser = game.player2 if game.winner == game.player1 else game.player1
        winning_side = 'Green' if game.random_result == 1 else 'Purple'

        # Commission info
        commission_logs = CommissionLog.objects.filter(game=game)
        commission_text = '\u2014'
        if commission_logs.exists():
            items_list = ', '.join([f"{c.item_name} ({c.item_value} SV)" for c in commission_logs])
            total_comm = sum(c.item_value for c in commission_logs)
            pct = commission_logs.first().actual_percent
            commission_text = f"{items_list}\nTotal: {total_comm} SV ({pct:.1f}%)"

        # Компактный description с основной инфой
        description = (
            f"🏆 **Winner:** {game.winner}\n"
            f"💀 **Loser:** {loser}\n"
            f"🎯 **Side:** {winning_side}\n"
            f"💰 **Total Pot:** {total_value} SV"
        )

        embed = {
            'title': f'🪙 Game #{game.id} — Coinflip Result',
            'description': description,
            'color': 0x00ff9d,
            'fields': [
                {
                    'name': '🟢 Player 1 (Creator)',
                    'value': f'**{game.player1}** — {game.value1} SV\n{p1_items or chr(8212)}',
                    'inline': True
                },
                {
                    'name': '🟣 Player 2 (Joiner)',
                    'value': f'**{game.player2}** — {game.value2} SV\n{p2_items or chr(8212)}',
                    'inline': True
                },
                {
                    'name': '🏦 Commission',
                    'value': commission_text,
                    'inline': False
                },
                {
                    'name': '🔒 Game Hash',
                    'value': f'```{game.game_hash or "N/A"}```',
                    'inline': False
                },
                {
                    'name': '🕐 Played At',
                    'value': f'<t:{played_timestamp}:F> (<t:{played_timestamp}:R>)',
                    'inline': True
                },
            ],
            'footer': {
                'text': '⚡ MMFLIP | Provably Fair',
                'icon_url': f'https://{settings.ALLOWED_HOSTS[0]}/static/img/logo.png' if settings.ALLOWED_HOSTS and settings.ALLOWED_HOSTS[0] != '*' else '',
            },
            'timestamp': now.isoformat(),
        }

        payload = {
            'username': 'MMFLIP Logs',
            'avatar_url': f'https://{settings.ALLOWED_HOSTS[0]}/static/img/logo.png' if settings.ALLOWED_HOSTS and settings.ALLOWED_HOSTS[0] != '*' else 'https://cdn-icons-png.flaticon.com/512/1001/1001371.png',
            'embeds': [embed]
        }

        resp = requests.post(webhook_url, json=payload, timeout=5)
        logger.info(f"[Discord Webhook] Game #{game.id} — Status: {resp.status_code}, Response: {resp.text[:200]}")
    except Exception as e:
        logger.error(f"[Discord Webhook] Game #{game.id} — EXCEPTION: {e}", exc_info=True)


def send_discord_log_async(game):
    """Отправляет лог в Discord в фоновом потоке, чтобы не замедлять ответ игроку"""
    t = threading.Thread(target=send_discord_game_log, args=(game,), daemon=True)
    t.start()

def get_bots_status():
    """Проверяет статус ботов через Roblox API"""
    try:
        bot_ids = [bot['id'] for bot in BOTS_CONFIG]

        # 1. Получаем статусы (Online/Offline)
        url_pres = "https://presence.roblox.com/v1/presence/users"
        resp_pres = requests.post(url_pres, json={"userIds": bot_ids})
        presences = {u['userId']: u['userPresenceType'] for u in resp_pres.json()['userPresences']}

        # 2. Получаем аватарки
        url_thumb = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={','.join(map(str, bot_ids))}&size=150x150&format=Png&isCircular=true"
        resp_thumb = requests.get(url_thumb)
        images = {d['targetId']: d['imageUrl'] for d in resp_thumb.json()['data']}

        bots_data = []
        for bot in BOTS_CONFIG:
            uid = bot['id']
            is_online = presences.get(uid, 0) == 2

            bots_data.append({
                'username': bot['username'],
                'image': images.get(uid, ''),
                'is_online': is_online,
                'status_text': 'In Game' if is_online else 'Offline',
                'link': "https://www.roblox.com/share?code=099c7510d8658b44812e08a857d316e7&type=Server"
            })
        return bots_data
    except:
        return []


def _normalize_username(username):
    return str(username or '').strip()


def _build_legacy_avatar_url(user_id, size='420x420'):
    try:
        width, height = str(size).lower().split('x', 1)
    except ValueError:
        width = height = '420'
    return f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width={width}&height={height}&format=png"


def get_roblox_avatar(username=None, user_id=None, size='420x420', is_circular=False, retries=4, retry_delay=0.75):
    username = _normalize_username(username)

    try:
        if user_id is None:
            user_id = get_roblox_id(username)

        if not user_id:
            return None

        url_thumb = "https://thumbnails.roblox.com/v1/users/avatar-headshot"
        params = {
            'userIds': user_id,
            'size': size,
            'format': 'Png',
            'isCircular': str(bool(is_circular)).lower(),
        }

        for attempt in range(retries):
            resp_thumb = requests.get(url_thumb, params=params, headers=ROBLOX_API_HEADERS, timeout=5)

            if resp_thumb.status_code == 200:
                data_thumb = resp_thumb.json().get('data') or []
                if data_thumb:
                    avatar_data = data_thumb[0]
                    image_url = avatar_data.get('imageUrl')
                    state = str(avatar_data.get('state') or '').lower()

                    if image_url:
                        return image_url

                    if state not in {'pending', 'blocked'}:
                        break
            else:
                print(f"❌ Ошибка API (Thumbnail): Код {resp_thumb.status_code}")

            if attempt < retries - 1:
                time.sleep(retry_delay)

        return _build_legacy_avatar_url(user_id, size=size)

    except Exception as e:
        print(f"❌ Критическая ошибка get_roblox_avatar: {e}")
        return _build_legacy_avatar_url(user_id, size=size) if user_id else None


def get_roblox_id(username):
    username = _normalize_username(username)
    if not username:
        return None

    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [username], "excludeBannedUsers": True}
    try:
        response = requests.post(url, json=payload, headers=ROBLOX_API_HEADERS, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data['data']: return data['data'][0]['id']
    except Exception as e:
        print(f"❌ Ошибка API (ID): {e}")
        return None
    return None


def get_roblox_blurb(user_id):
    url = f"https://users.roblox.com/v1/users/{user_id}"
    try:
        response = requests.get(url, headers=ROBLOX_API_HEADERS, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get('description', '')
    except:
        return ""


# ==========================================
# 2. VIEW ФУНКЦИИ (СТРАНИЦЫ)
# ==========================================

# --- ГЛАВНАЯ (DASHBOARD) ---
@ensure_csrf_cookie
def home(request):
    total_profit = 0
    inventory_count = 0
    inventory_items = []
    avatar_url = None
    bots_data = get_bots_status()  # Получаем ботов для модального окна

    if request.user.is_authenticated:
        avatar_url = get_cached_avatar(request.user.username)

        inventory_items = UserItem.objects.filter(
            owner_name__iexact=request.user.username,
            status='available'
        )
        inventory_count = inventory_items.count()

        current_assets = UserItem.objects.filter(owner_name__iexact=request.user.username, status='available')
        total_profit = current_assets.aggregate(Sum('item_value'))['item_value__sum'] or 0

    # Последние 50 завершённых игр для горизонтальной ленты
    recent_games = CoinflipGame.objects.filter(
        is_active=False,
        winner__isnull=False
    ).order_by('-created_at')[:50]

    # === GIVEAWAYS ===
    # Автоматически завершаем истёкшие розыгрыши
    _resolve_expired_giveaways()

    active_giveaways = Giveaway.objects.filter(is_active=True).order_by('-item_value')

    # Собираем аватарки создателей
    ga_creators = set(g.creator for g in active_giveaways)
    ga_avatars = {}
    for name in ga_creators:
        ga_avatars[name] = get_cached_avatar(name)

    # Собираем ID розыгрышей, в которых юзер уже участвует
    joined_giveaway_ids = []
    if request.user.is_authenticated:
        for g in active_giveaways:
            if request.user.username.lower() in [p.lower() for p in (g.participants or [])]:
                joined_giveaway_ids.append(g.id)

    context = {
        'user': request.user,
        'inventory_items': inventory_items,
        'total_profit': total_profit,
        'inventory_count': inventory_count,
        'avatar_url': avatar_url,
        'bots_data': bots_data,
        'recent_games': recent_games,
        'active_giveaways': active_giveaways,
        'ga_avatars': ga_avatars,
        'joined_giveaway_ids': joined_giveaway_ids,
        'title': 'Dashboard'
    }
    return render(request, 'home.html', context)


# --- ИСТОРИЯ (TRADE / ADMIN) ---
def trade(request):
    if not request.user.is_authenticated:
        return redirect('home')

    bots_data = get_bots_status()

    avatar_url = get_cached_avatar(request.user.username)

    if request.user.is_superuser:
        logs = TradeLog.objects.all().order_by('-created_at')
        mode = 'admin'
    else:
        logs = CoinflipGame.objects.filter(
            Q(player1__iexact=request.user.username) |
            Q(player2__iexact=request.user.username),
            is_active=False
        ).order_by('-created_at')[:50]
        mode = 'user'

    # Deposit logs (trades TO bot = deposits)
    deposit_logs = TradeLog.objects.filter(
        sender_name__iexact=request.user.username
    ).order_by('-created_at')[:50]

    # Withdraw logs
    withdraw_logs = WithdrawRequest.objects.filter(
        user_name__iexact=request.user.username
    ).order_by('-created_at')[:50]

    # Collect avatars for all players in game history
    game_avatars = {}
    if mode == 'user':
        players_set = set()
        for g in logs:
            players_set.add(g.player1)
            if g.player2:
                players_set.add(g.player2)
        for p_name in players_set:
            game_avatars[p_name] = get_cached_avatar(p_name)

    # Collect bot avatars from bots_data
    bot_avatars = {}
    for bot in bots_data:
        bot_avatars[bot['username']] = bot.get('image', DEFAULT_AVATAR_URL)

    # Also resolve avatars for all bot names from deposit logs
    # (bot_name in TradeLog may differ from BOTS_CONFIG usernames)
    deposit_bot_names = set(dep.bot_name for dep in deposit_logs if dep.bot_name)
    for bot_name in deposit_bot_names:
        if bot_name not in bot_avatars:
            bot_avatars[bot_name] = get_cached_avatar(bot_name)

    # ── Build comprehensive item_name → image_url lookup ──
    # Source 1: UserItem records (prioritize rbxcdn URLs)
    item_images = {}
    for ui in UserItem.objects.exclude(image_url='').values('item_name', 'image_url'):
        name = ui['item_name']
        url = ui['image_url']
        existing = item_images.get(name, '')
        if not existing:
            item_images[name] = url
        elif 'rbxcdn.com' in url and 'rbxcdn.com' not in existing:
            item_images[name] = url  # prefer rbxcdn over wikia/roblox.com/asset

    # Source 2: CoinflipGame items that already have embedded images
    for g_img in CoinflipGame.objects.filter(is_active=False):
        for item in (g_img.items1 or []) + (g_img.items2 or []):
            if isinstance(item, dict) and item.get('image') and item.get('name'):
                name = item['name']
                url = item['image']
                existing = item_images.get(name, '')
                if not existing:
                    item_images[name] = url
                elif 'rbxcdn.com' in url and 'rbxcdn.com' not in existing:
                    item_images[name] = url

    def _resolve_item_image(item_name):
        """Resolve image URL with fuzzy matching for names like 'Cotton Candy (x2)'"""
        # Exact match first
        url = item_images.get(item_name, '')
        if url:
            return url
        # Strip quantity suffix: "Frostfade (xx2)" → "Frostfade", "Cotton Candy (x2)" → "Cotton Candy"
        base_name = re.sub(r'\s*\(x+\d+\)\s*$', '', item_name).strip()
        if base_name != item_name:
            url = item_images.get(base_name, '')
            if url:
                return url
        return ''

    # Enrich game logs with item images (fill missing from lookup)
    if mode == 'user':
        for g in logs:
            for item in (g.items1 or []):
                if isinstance(item, dict) and not item.get('image'):
                    item['image'] = _resolve_item_image(item.get('name', ''))
            for item in (g.items2 or []):
                if isinstance(item, dict) and not item.get('image'):
                    item['image'] = _resolve_item_image(item.get('name', ''))

    # Enrich deposit logs: convert item name strings to dicts with images
    enriched_deposits = []
    for dep in deposit_logs:
        items_with_images = []
        for item_name in (dep.items or []):
            items_with_images.append({
                'name': item_name,
                'image': _resolve_item_image(item_name),
            })
        enriched_deposits.append({
            'bot_name': dep.bot_name,
            'items': items_with_images,
            'created_at': dep.created_at,
        })

    # Enrich withdraw logs with images
    enriched_withdrawals = []
    for wd in withdraw_logs:
        enriched_withdrawals.append({
            'item_name': wd.item_name,
            'amount': wd.amount,
            'is_completed': wd.is_completed,
            'created_at': wd.created_at,
            'image': _resolve_item_image(wd.item_name),
        })

    context = {
        'logs': logs,
        'mode': mode,
        'bots_data': bots_data,
        'title': 'History',
        'avatar_url': avatar_url,
        'deposit_logs': enriched_deposits,
        'withdraw_logs': enriched_withdrawals,
        'game_avatars': game_avatars,
        'bot_avatars': bot_avatars,
        'default_avatar': DEFAULT_AVATAR_URL,
    }
    return render(request, 'trade.html', context)


# --- COINFLIP ГЛАВНАЯ ---
@ensure_csrf_cookie
def coinflip_home(request):
    active_games = CoinflipGame.objects.filter(is_active=True).order_by('-created_at')
    bots_data = get_bots_status()

    avatar_url = get_cached_avatar(request.user.username)

    my_inventory = []
    total_value = 0
    profit_all = 0
    profit_7d = 0
    profit_today = 0
    games_won = 0
    games_lost = 0

    if request.user.is_authenticated:
        my_inventory = UserItem.objects.filter(
            owner_name__iexact=request.user.username,
            status='available'
        )
        total_value = my_inventory.aggregate(Sum('item_value'))['item_value__sum'] or 0

        # --- PROFIT CALCULATIONS ---
        uname = request.user.username
        finished = CoinflipGame.objects.filter(
            Q(player1__iexact=uname) | Q(player2__iexact=uname),
            is_active=False
        )

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timezone.timedelta(days=7)

        def calc_profit(qs):
            p = 0
            w = 0
            l = 0
            for g in qs:
                is_p1 = g.player1.lower() == uname.lower()
                my_bet = g.value1 if is_p1 else g.value2
                won = g.winner and g.winner.lower() == uname.lower()
                if won:
                    p += (g.value1 + g.value2) - my_bet
                    w += 1
                else:
                    p -= my_bet
                    l += 1
            return p, w, l

        profit_all, games_won, games_lost = calc_profit(finished)
        profit_7d, _, _ = calc_profit(finished.filter(created_at__gte=week_ago))
        profit_today, _, _ = calc_profit(finished.filter(created_at__gte=today_start))

    # --- СОБИРАЕМ АВАТАРКИ ДЛЯ ИГРОКОВ ---
    # Чтобы не делать 100 запросов, соберем уникальные ники
    players_set = set()
    for g in active_games:
        players_set.add(g.player1)
        if g.player2: players_set.add(g.player2)

    avatars = {}
    for p_name in players_set:
        avatars[p_name] = get_cached_avatar(p_name)

    # --- АНИМАЦИЯ ---
    flip_data = None
    flip_id = request.GET.get('flip_game')
    if flip_id:
        try:
            game = CoinflipGame.objects.get(id=flip_id)
            flip_data = {
                'player1': game.player1,
                'player2': game.player2,
                'winner': game.winner,
                'total_bet': game.value1 + game.value2,
                'result_code': game.random_result,
                'game_hash': game.game_hash or 'N/A',
            }
        except CoinflipGame.DoesNotExist:
            pass

    context = {
        'games': active_games,
        'inventory': my_inventory,
        'total_value': total_value,
        'profit_all': profit_all,
        'profit_7d': profit_7d,
        'profit_today': profit_today,
        'games_won': games_won,
        'games_lost': games_lost,
        'flip_data': flip_data,
        'bots_data': bots_data,
        'avatars': avatars,
        'title': 'Coinflip',
        'avatar_url': avatar_url,
        'online_count': _online_count_safe(),
    }
    return render(request, 'coinflip.html', context)


def _online_count_safe():
    try:
        from casino.visit_logger import get_online_count
        return get_online_count()
    except Exception:
        return 0


# ==========================================
# 3. ИГРОВАЯ ЛОГИКА (CREATE, JOIN, CANCEL)
# ==========================================


def apply_commission(game, winner):
    """
    Система комиссии:
    - Сумма ставок обоих игроков > 50
    - Общее кол-во предметов > 4
    - Цель: ~10% от банка
    - Может забрать несколько предметов (добирает до цели)
    - Если нет идеального — берёт ближайший, даже если дороже цели
    - Комиссия берётся ВСЕГДА при выполнении условий
    """
    total_pot = (game.value1 or 0) + (game.value2 or 0)
    all_items = (game.items1 or []) + (game.items2 or [])
    total_items_count = len(all_items)

    logger.warning(f"[COMMISSION] Game #{game.id} | Winner: {winner} | Pot: {total_pot} | Items: {total_items_count}")
    print(f"[COMMISSION] Game #{game.id} | Winner: {winner} | Pot: {total_pot} | Items: {total_items_count}")

    # Условие 1: сумма ставок обоих игроков > 50
    if total_pot <= 50:
        logger.warning(f"[COMMISSION] Game #{game.id} — SKIPPED: pot {total_pot} <= 50")
        print(f"[COMMISSION] Game #{game.id} — SKIPPED: pot {total_pot} <= 50")
        return None

    # Условие 2: предметов в сумме > 4
    if total_items_count <= 4:
        logger.warning(f"[COMMISSION] Game #{game.id} — SKIPPED: items {total_items_count} <= 4")
        print(f"[COMMISSION] Game #{game.id} — SKIPPED: items {total_items_count} <= 4")
        return None

    target = total_pot * 0.10  # Цель — 10% от банка
    min_comm = total_pot * 0.05   # 5%
    max_comm = total_pot * 0.15   # 15%

    # Собираем ID предметов из этой игры
    game_item_ids = set()
    for item_data in all_items:
        if isinstance(item_data, dict) and 'id' in item_data:
            game_item_ids.add(item_data['id'])

    # Предметы победителя из этой игры
    candidates = list(UserItem.objects.filter(
        id__in=game_item_ids,
        owner_name__iexact=winner,
        status='available'
    ).order_by('item_value'))

    if not candidates:
        logger.warning(f"[COMMISSION] Game #{game.id} — SKIPPED: no candidates found! IDs: {game_item_ids}")
        print(f"[COMMISSION] Game #{game.id} — SKIPPED: no candidates found! IDs: {game_item_ids}")
        return None

    logger.warning(f"[COMMISSION] Game #{game.id} — Found {len(candidates)} candidates, target: {target:.1f} SV")
    print(f"[COMMISSION] Game #{game.id} — Found {len(candidates)} candidates, target: {target:.1f} SV")
    selected = []

    # === Стратегия 1: один предмет в диапазоне 5-15%, ближайший к 10% ===
    best_single_in_range = None
    best_diff = float('inf')
    for item in candidates:
        if min_comm <= item.item_value <= max_comm:
            diff = abs(item.item_value - target)
            if diff < best_diff:
                best_diff = diff
                best_single_in_range = item

    if best_single_in_range:
        selected = [best_single_in_range]
    else:
        # === Стратегия 2: набираем несколькими дешёвыми предметами до цели ===
        sorted_cheap = sorted(candidates, key=lambda x: x.item_value)
        combo = []
        combo_sum = 0
        for item in sorted_cheap:
            if combo_sum >= target:
                break
            combo.append(item)
            combo_sum += item.item_value

        # === Стратегия 3: один ближайший к цели (даже если дороже) ===
        closest_single = min(candidates, key=lambda x: abs(x.item_value - target))
        single_diff = abs(closest_single.item_value - target)
        combo_diff = abs(combo_sum - target) if combo else float('inf')

        # Выбираем что ближе к цели: комбо из дешёвых или один предмет
        if combo and combo_diff <= single_diff:
            selected = combo
        else:
            selected = [closest_single]

    if not selected:
        return None

    # === Забираем выбранные предметы ===
    taken_value = sum(i.item_value for i in selected)
    actual_percent = (taken_value / total_pot) * 100 if total_pot > 0 else 0

    logger.warning(f"[COMMISSION] Game #{game.id} — TAKING {len(selected)} items, value: {taken_value} SV ({actual_percent:.1f}%)")
    print(f"[COMMISSION] Game #{game.id} — TAKING {len(selected)} items, value: {taken_value} SV ({actual_percent:.1f}%)")

    commission_logs = []
    for item in selected:
        cl = CommissionLog.objects.create(
            game=game,
            winner=winner,
            item_name=item.item_name,
            item_value=item.item_value,
            item_id=item.id,
            total_pot=total_pot,
            total_items=total_items_count,
            target_commission=target,
            actual_percent=actual_percent,
        )
        commission_logs.append(cl)
        # Помечаем предмет как комиссию и переносим на виртуальный house-аккаунт
        item.status = 'available'
        item.owner_name = COMMISSION_OWNER
        item.item_name = f"{item.item_name} [COMM #{game.id}]"
        item.save()
        logger.warning(f"[COMMISSION] Game #{game.id} — Took: {item.item_name} ({item.item_value} SV) -> {COMMISSION_OWNER}")
        print(f"[COMMISSION] Game #{game.id} — Took: {item.item_name} ({item.item_value} SV) -> {COMMISSION_OWNER}")

    return commission_logs

@login_required
@ratelimit(key='user', rate='10/m', block=False)
def create_game(request):
    if request.method != 'POST':
        return redirect('coinflip')

    if getattr(request, 'limited', False):
        messages.error(request, "Too many games created. Slow down.")
        return redirect('coinflip')

    last_game = CoinflipGame.objects.filter(
        player1=request.user.username
    ).order_by('-created_at').first()

    if last_game and (timezone.now() - last_game.created_at).total_seconds() < 5:
        messages.error(request, "Please wait a few seconds before creating another game.")
        return redirect('coinflip')

    selected_ids = request.POST.getlist('items')
    side = request.POST.get('side', 'green')
    if side not in ['green', 'yellow']:
        side = 'green'

    if not selected_ids:
        messages.error(request, "Select items to bet!")
        return redirect('coinflip')

    try:
        with transaction.atomic():
            items = list(
                UserItem.objects.select_for_update().filter(
                    id__in=selected_ids,
                    owner_name__iexact=request.user.username,
                    status='available',
                )
            )
            if not items:
                messages.error(request, "Selected items unavailable.")
                return redirect('coinflip')

            total_bet = sum(item.item_value for item in items)
            if total_bet < 10:
                messages.error(request, "Minimum bet is 10 value.")
                return redirect('coinflip')

            items_json = []
            for item in items:
                item.status = 'betting'
                item.save(update_fields=['status'])
                items_json.append({
                    'id': item.id,
                    'name': item.item_name,
                    'value': item.item_value,
                    'image': item.image_url,
                })

            game = CoinflipGame.objects.create(
                player1=request.user.username,
                items1=items_json,
                value1=total_bet,
                creator_side=side,
                is_active=True,
            )

            for it in items:
                log_item_action(request.user.username, 'bet_lock', item=it,
                                related_game_id=game.id, request=request)
    except Exception as exc:
        logger.exception("create_game failed: %s", exc)
        messages.error(request, "Could not create game. Try again.")
        return redirect('coinflip')

    messages.success(request, f"Game created on {side.upper()} side!")
    return redirect('coinflip')


@login_required
@ratelimit(key='user', rate='20/m', block=False)
def join_game(request, game_id):
    if request.method != 'POST':
        return redirect('coinflip')

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if getattr(request, 'limited', False):
        msg = "Too many actions, slow down."
        if is_ajax: return JsonResponse({'status': 'error', 'message': msg}, status=429)
        messages.error(request, msg)
        return redirect('coinflip')

    selected_ids = request.POST.getlist('items')

    try:
        with transaction.atomic():
            game = CoinflipGame.objects.select_for_update().filter(id=game_id, is_active=True).first()
            if not game:
                msg = "Game not available."
                if is_ajax: return JsonResponse({'status': 'error', 'message': msg})
                messages.error(request, msg)
                return redirect('coinflip')

            if game.player2:
                msg = "Game already has a second player."
                if is_ajax: return JsonResponse({'status': 'error', 'message': msg})
                messages.error(request, msg)
                return redirect('coinflip')

            if game.player1.lower() == request.user.username.lower():
                msg = "You cannot join your own game!"
                if is_ajax: return JsonResponse({'status': 'error', 'message': msg})
                messages.error(request, msg)
                return redirect('coinflip')

            if not selected_ids:
                msg = "Select items to match the bet!"
                if is_ajax: return JsonResponse({'status': 'error', 'message': msg})
                messages.error(request, msg)
                return redirect('coinflip')

            items = list(
                UserItem.objects.select_for_update().filter(
                    id__in=selected_ids,
                    owner_name__iexact=request.user.username,
                    status='available',
                )
            )
            total_bet_p2 = sum(item.item_value for item in items)

            min_req = game.min_join_value()
            max_req = game.max_join_value()

            if total_bet_p2 < 10:
                msg = "Minimum bet is 10!"
                if is_ajax: return JsonResponse({'status': 'error', 'message': msg})
                messages.error(request, msg)
                return redirect('coinflip')
            if not (min_req <= total_bet_p2 <= max_req):
                msg = f"Bet out of range ({min_req}-{max_req})"
                if is_ajax: return JsonResponse({'status': 'error', 'message': msg})
                messages.error(request, msg)
                return redirect('coinflip')

            items_json_p2 = []
            for item in items:
                item.status = 'betting'
                item.save(update_fields=['status'])
                items_json_p2.append({
                    'id': item.id, 'name': item.item_name, 'value': item.item_value, 'image': item.image_url,
                })
                log_item_action(request.user.username, 'bet_lock', item=item,
                                related_game_id=game.id, request=request)

            # Криптографически стойкий генератор + game_hash ниже = provably fair
            result = secrets.randbelow(2) + 1

            winning_side_num = 1 if game.creator_side == 'green' else 2
            winner = game.player1 if result == winning_side_num else request.user.username
            loser = request.user.username if winner == game.player1 else game.player1

            game_hash = generate_game_hash(
                game.id, game.player1, request.user.username,
                result, settings.SECRET_KEY,
            )

            game.player2 = request.user.username
            game.items2 = items_json_p2
            game.value2 = total_bet_p2
            game.winner = winner
            game.random_result = result
            game.game_hash = game_hash
            game.is_active = False
            game.save()

            all_items_json = game.items1 + game.items2
            for i in all_items_json:
                try:
                    db_item = UserItem.objects.select_for_update().get(id=i['id'])
                    prev_owner = db_item.owner_name
                    db_item.owner_name = winner
                    db_item.status = 'available'
                    db_item.save(update_fields=['owner_name', 'status'])
                    log_item_action(winner, 'won', item=db_item,
                                    related_game_id=game.id, request=request)
                    if prev_owner.lower() != winner.lower():
                        log_item_action(prev_owner, 'lost', item=db_item,
                                        related_game_id=game.id, request=request)
                except UserItem.DoesNotExist:
                    logger.warning("join_game: item id %s missing", i.get('id'))

            commission = apply_commission(game, winner)

        send_discord_log_async(game)
    except Exception as exc:
        logger.exception("join_game failed: %s", exc)
        msg = "Could not join game. Try again."
        if is_ajax: return JsonResponse({'status': 'error', 'message': msg}, status=500)
        messages.error(request, msg)
        return redirect('coinflip')

    if is_ajax:
        return JsonResponse({'status': 'success'})
    return redirect('coinflip')


@login_required
def cancel_game(request, game_id):
    if request.method != 'POST':
        return redirect('coinflip')

    try:
        with transaction.atomic():
            game = CoinflipGame.objects.select_for_update().filter(id=game_id).first()
            if not game:
                return redirect('coinflip')
            if game.player1.lower() != request.user.username.lower() or game.player2:
                return redirect('coinflip')

            for item_data in game.items1:
                try:
                    db_item = UserItem.objects.select_for_update().get(id=item_data['id'])
                    if db_item.owner_name.lower() == request.user.username.lower():
                        db_item.status = 'available'
                        db_item.save(update_fields=['status'])
                        log_item_action(request.user.username, 'bet_unlock', item=db_item,
                                        related_game_id=game.id, note='cancel_game', request=request)
                except UserItem.DoesNotExist:
                    pass

            game.delete()
    except Exception as exc:
        logger.exception("cancel_game failed: %s", exc)
        messages.error(request, "Could not cancel game.")
        return redirect('coinflip')

    messages.success(request, "Game cancelled.")
    return redirect('coinflip')


# ==========================================
# 4. ADMIN & AUTH & API
# ==========================================

@login_required
@require_POST
def add_test_item(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('coinflip')

    if request.method == 'POST':
        item_name = request.POST.get('item_name')
        try:
            item_value = int(request.POST.get('item_value'))
        except:
            item_value = 10

        UserItem.objects.create(
            owner_name=request.user.username,
            item_name=item_name,
            item_value=item_value,
            status='available'
        )
        messages.success(request, f"Added {item_name}")

    return redirect('coinflip')


def _send_discord_embed(webhook_url, title, description, color=0x3498db, fields=None):
    """Универсальная отправка embed в Discord вебхук"""
    try:
        if not webhook_url:
            return
        embed = {
            'title': title,
            'description': description,
            'color': color,
            'timestamp': timezone.now().isoformat(),
        }
        if fields:
            embed['fields'] = fields
        payload = {'embeds': [embed]}
        threading.Thread(
            target=lambda: requests.post(webhook_url, json=payload, timeout=5),
            daemon=True
        ).start()
    except Exception as e:
        logger.error(f'[Discord Webhook] Error: {e}')


def send_event_log(title, description, color=0x3498db, fields=None):
    """Лог событий (логины и т.д.)"""
    _send_discord_embed(getattr(settings, 'DISCORD_EVENTS_WEBHOOK_URL', ''), title, description, color, fields)


def send_admin_log(title, description, color=0xf39c12, fields=None):
    """Лог действий админа"""
    _send_discord_embed(getattr(settings, 'DISCORD_ADMIN_WEBHOOK_URL', ''), title, description, color, fields)


def send_trade_log(title, description, color=0x2ecc71, fields=None):
    """Лог депозитов и выводов"""
    _send_discord_embed(getattr(settings, 'DISCORD_TRADES_WEBHOOK_URL', ''), title, description, color, fields)


def admin_panel(request):
    """Admin panel for superusers to manage items & inventory"""
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('home')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_item':
            owner = request.POST.get('owner_name', request.user.username).strip()
            item_name = request.POST.get('item_name', 'Currency').strip()
            try:
                item_value = int(request.POST.get('item_value', 0))
            except (ValueError, TypeError):
                item_value = 0
            try:
                amount = int(request.POST.get('amount', 1))
            except (ValueError, TypeError):
                amount = 1
            image_url = request.POST.get('image_url', '').strip()

            # Создаём amount штук отдельных предметов
            for _ in range(max(1, amount)):
                UserItem.objects.create(
                    owner_name=owner,
                    item_name=item_name,
                    item_value=item_value,
                    amount=1,
                    image_url=image_url,
                    status='available'
                )
            messages.success(request, f'Added "{item_name}" ×{amount} ({item_value} SV each) to {owner}')
            send_admin_log(
                '➕ Admin Add Item',
                f'**Admin:** {request.user.username}\n**Owner:** {owner}\n**Item:** {item_name} ×{amount}\n**Value:** {item_value} SV each',
                color=0x2ecc71
            )

        elif action == 'quick_add':
            try:
                value = int(request.POST.get('preset_value', 100))
            except (ValueError, TypeError):
                value = 100
            UserItem.objects.create(
                owner_name=request.user.username,
                item_name=f'Currency ({value} SV)',
                item_value=value,
                amount=1,
                image_url='',
                status='available'
            )
            messages.success(request, f'Added {value} SV currency to your inventory')
            send_admin_log(
                '⚡ Admin Quick Add',
                f'**Admin:** {request.user.username}\n**Value:** {value} SV',
                color=0xf1c40f
            )

        elif action == 'delete_item':
            item_id = request.POST.get('item_id')
            try:
                item = UserItem.objects.get(id=item_id)
                name = item.item_name
                owner = item.owner_name
                val = item.item_value
                item.delete()
                messages.success(request, f'Deleted item #{item_id}')
                send_admin_log(
                    '🗑️ Admin Delete Item',
                    f'**Admin:** {request.user.username}\n**Owner:** {owner}\n**Item:** {name} ({val} SV)\n**ID:** #{item_id}',
                    color=0xe74c3c
                )
            except UserItem.DoesNotExist:
                messages.error(request, 'Item not found')

        elif action == 'lookup_user':
            lookup_name = request.POST.get('lookup_username', '').strip()
            if lookup_name:
                request.session['admin_lookup_user'] = lookup_name
            return redirect('admin_panel')

        elif action == 'clear_lookup':
            if 'admin_lookup_user' in request.session:
                del request.session['admin_lookup_user']
            return redirect('admin_panel')

        elif action == 'clear_chat':
            count = ChatMessage.objects.count()
            ChatMessage.objects.all().delete()
            messages.success(request, f'Chat cleared — {count} messages deleted')
            send_admin_log(
                '🧹 Admin Clear Chat',
                f'**Admin:** {request.user.username}\n**Deleted:** {count} messages',
                color=0xe67e22
            )

        elif action == 'delete_user_item':
            item_id = request.POST.get('item_id')
            try:
                item = UserItem.objects.get(id=item_id)
                owner = item.owner_name
                name = item.item_name
                item.delete()
                messages.success(request, f'Deleted "{name}" from {owner} (#{item_id})')
                send_admin_log(
                    '🗑️ Admin Deleted User Item',
                    f'**Admin:** {request.user.username}\n**Owner:** {owner}\n**Item:** {name} (#{item_id})',
                    color=0xff4b4b
                )
            except UserItem.DoesNotExist:
                messages.error(request, 'Item not found')
            return redirect('admin_panel')

        elif action == 'reset_user_withdrawals':
            target = request.POST.get('target_username', '').strip()
            if not target:
                messages.error(request, 'Username required')
                return redirect('admin_panel')
            try:
                with transaction.atomic():
                    pending = WithdrawRequest.objects.select_for_update().filter(
                        user_name__iexact=target, is_completed=False
                    )
                    count = pending.count()
                    UserItem.objects.filter(
                        owner_name__iexact=target, status='withdrawing'
                    ).update(status='available')
                    pending.delete()
                messages.success(request, f'♻️ Reset {count} pending withdrawal(s) for {target}')
                send_admin_log(
                    '♻️ Reset User Withdrawals',
                    f'**Admin:** {request.user.username}\n**Target:** {target}\n**Reset:** {count} request(s)',
                    color=0xe67e22
                )
            except Exception as e:
                logger.warning('reset_user_withdrawals failed: %s', e)
                messages.error(request, 'Failed to reset withdrawals')
            return redirect('admin_panel')

        elif action == 'force_end_giveaway':
            ga_id = request.POST.get('giveaway_id')
            try:
                giveaway = Giveaway.objects.get(id=ga_id, is_active=True)
                participants = giveaway.participants or []
                if participants:
                    winner = secrets.choice(participants)
                    giveaway.winner = winner
                    UserItem.objects.create(
                        owner_name=winner,
                        item_name=giveaway.item_name,
                        item_value=giveaway.item_value,
                        image_url=giveaway.item_image,
                        status='available'
                    )
                    messages.success(request, f'Giveaway ended! Winner: {winner}')
                else:
                    UserItem.objects.create(
                        owner_name=giveaway.creator,
                        item_name=giveaway.item_name,
                        item_value=giveaway.item_value,
                        image_url=giveaway.item_image,
                        status='available'
                    )
                    giveaway.winner = None
                    messages.success(request, f'Giveaway ended with no participants. Item returned to {giveaway.creator}.')
                giveaway.is_active = False
                giveaway.save()
                send_admin_log(
                    '🎉 Admin Force End Giveaway',
                    f'**Admin:** {request.user.username}\n**Giveaway:** {giveaway.item_name} ({giveaway.item_value} SV)\n**Winner:** {giveaway.winner or "No participants"}',
                    color=0x9b59b6
                )
            except Giveaway.DoesNotExist:
                messages.error(request, 'Giveaway not found or already ended.')

        return redirect('admin_panel')

    # GET — show panel
    inventory = UserItem.objects.filter(
        owner_name__iexact=request.user.username,
        status='available'
    ).order_by('-received_at')
    total_value = inventory.aggregate(Sum('item_value'))['item_value__sum'] or 0

    bots_data = get_bots_status()
    avatar_url = get_cached_avatar(request.user.username)
    presets = [10, 50, 100, 250, 500, 1000, 5000]

    # Active giveaways for management
    active_giveaways = Giveaway.objects.filter(is_active=True).order_by('-created_at')

    # Lookup user
    lookup_username = request.session.get('admin_lookup_user', '')
    lookup_inventory = []
    lookup_games = []
    lookup_total = 0
    lookup_roblox_id = None
    lookup_pending_withdrawals = []
    if lookup_username:
        lookup_pending_withdrawals = WithdrawRequest.objects.filter(
            user_name__iexact=lookup_username, is_completed=False
        ).order_by('-created_at')
        lookup_inventory = UserItem.objects.filter(
            owner_name__iexact=lookup_username,
            status='available'
        ).order_by('-received_at')
        lookup_total = lookup_inventory.aggregate(Sum('item_value'))['item_value__sum'] or 0
        lookup_games = CoinflipGame.objects.filter(
            Q(player1__iexact=lookup_username) | Q(player2__iexact=lookup_username)
        ).order_by('-created_at')[:20]
        lookup_roblox_id = get_roblox_id(lookup_username)

    return render(request, 'admin_panel.html', {
        'inventory': inventory,
        'total_value': total_value,
        'presets': presets,
        'bots_data': bots_data,
        'avatar_url': avatar_url,
        'active_giveaways': active_giveaways,
        'lookup_username': lookup_username,
        'lookup_inventory': lookup_inventory,
        'lookup_games': lookup_games,
        'lookup_total': lookup_total,
        'lookup_roblox_id': lookup_roblox_id,
        'lookup_pending_withdrawals': lookup_pending_withdrawals,
    })


@csrf_exempt
def accept_trade_log(request):
    if not _bot_token_ok(request):
        return JsonResponse({'status': 'error', 'message': 'forbidden'}, status=403)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            bot_name = data.get('bot_name', 'Unknown')
            sender_name = data.get('sender_name', 'Unknown')
            items_data = data.get('items', [])

            print(f"📥 Получен депозит от {sender_name}. Предметов: {len(items_data)}")

            # 1. Лог истории
            item_names_only = [i['name'] for i in items_data]
            TradeLog.objects.create(bot_name=bot_name, sender_name=sender_name, items=item_names_only)

            # 2. Сохранение в инвентарь
            for item in items_data:
                try:
                    qty = int(item.get('amount', 1))
                    raw_image = item.get('image', '')

                    # Конвертируем ссылку и валидируем (whitelist доменов, защита от XSS)
                    clean_image_url = safe_image_url(convert_asset_to_url(raw_image))

                    # Создаем QTY карточек
                    for _ in range(qty):
                        new_item = UserItem.objects.create(
                            owner_name=sender_name,
                            item_name=item['name'],
                            item_value=item.get('value', 0),
                            image_url=clean_image_url,
                            status='available'
                        )
                        log_item_action(sender_name, 'create', item=new_item,
                                        note=f'deposit via {bot_name}', request=request)
                except Exception as e_item:
                    print(f"⚠️ Ошибка с предметом {item.get('name')}: {e_item}")
                    continue  # Пропускаем битый предмет, но сохраняем остальные

            # Лог депозита в Discord
            items_str = ', '.join([f"{i['name']} x{i.get('amount',1)} ({i.get('value',0)} SV)" for i in items_data])
            total_val = sum(i.get('value', 0) * int(i.get('amount', 1)) for i in items_data)
            send_trade_log(
                '📥 Deposit',
                f'**User:** {sender_name}\n**Bot:** {bot_name}\n**Items:** {items_str}\n**Total:** {total_val} SV',
                color=0x2ecc71
            )

            print("✅ Депозит успешно сохранен!")
            return JsonResponse({'status': 'success'})

        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА ДЕПОЗИТА: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error'}, status=405)


# === ЛОГИКА АВТОРИЗАЦИИ (JSON) ===


@ratelimit(key='ip', rate='10/m', block=False)
def robox_login(request):
    """Шаг 1: Принимаем ник, находим ID, генерируем код"""
    if getattr(request, 'limited', False):
        return JsonResponse({'status': 'error', 'message': 'Too many login attempts'}, status=429)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')

            if not username:
                return JsonResponse({'status': 'error', 'message': 'Enter username!'})

            user_id = get_roblox_id(username)
            if not user_id:
                return JsonResponse({'status': 'error', 'message': 'User not found in Roblox!'})

            # Генерируем код
            random_code = "MMF-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

            # Сохраняем в сессию
            request.session['auth_roblox_user'] = username
            request.session['auth_roblox_id'] = user_id
            request.session['auth_code'] = random_code
            request.session.save()  # Принудительно сохраняем

            # Получаем аватарку для красоты
            avatar = get_roblox_avatar(username)

            return JsonResponse({
                'status': 'success',
                'code': random_code,
                'username': username,
                'avatar': avatar
            })
        except Exception as e:
            print(f"Login error: {e}")
            return JsonResponse({'status': 'error', 'message': 'Server error'})

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'})


@ratelimit(key='ip', rate='20/m', block=False)
def verify_page(request):
    """Шаг 2: Проверяем код в описании"""
    if getattr(request, 'limited', False):
        return JsonResponse({'status': 'error', 'message': 'Too many verification attempts'}, status=429)
    if request.method == 'POST':
        if 'auth_code' not in request.session:
            return JsonResponse({'status': 'error', 'message': 'Session expired. Try again.'})

        code = request.session['auth_code']
        username = request.session['auth_roblox_user']
        user_id = request.session['auth_roblox_id']

        try:
            # Проверяем описание в Роблокс
            current_blurb = get_roblox_blurb(user_id)

            if code in current_blurb:
                # Создаем или получаем юзера
                user, created = User.objects.get_or_create(username=username)
                # Защита от session fixation: выдаём новый session key
                request.session.cycle_key()
                login(request, user)

                # Логируем вход в Discord
                send_event_log(
                    '🔑 User Login',
                    f'**Username:** {username}\n**Roblox ID:** {user_id}\n**New user:** {"Yes" if created else "No"}',
                    color=0x00ff9d,
                    fields=[
                        {'name': 'IP', 'value': request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "unknown")), 'inline': True},
                    ]
                )

                # Чистим сессию
                del request.session['auth_code']

                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Code not found in bio! Wait 10s and try again.'
                })
        except Exception as e:
            logger.warning("verify_page failed: %s", e)
            return JsonResponse({'status': 'error', 'message': 'Verification failed. Try again.'})

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'})


def logout_user(request):
    logout(request)
    return redirect('home')


@login_required
@require_POST
@ratelimit(key='user', rate='10/m', block=False)
def withdraw_item(request):
    if getattr(request, 'limited', False):
        return JsonResponse({'status': 'error', 'message': 'Too many withdraw requests'}, status=429)
    item_id = request.POST.get('item_id')
    try:
        with transaction.atomic():
            item = UserItem.objects.select_for_update().get(
                id=item_id, owner_name__iexact=request.user.username, status='available'
            )
            item.status = 'withdrawing'
            item.save(update_fields=['status'])

            WithdrawRequest.objects.create(
                user_name=request.user.username,
                item_name=item.item_name,
                amount=item.amount,
            )
            log_item_action(request.user.username, 'withdraw_request', item=item, request=request)
            send_trade_log(
                '📤 Withdraw Request',
                f'**User:** {request.user.username}\n**Item:** {item.item_name}\n**Value:** {item.item_value} SV\n**Item ID:** #{item.id}',
                color=0xe74c3c
            )
        return JsonResponse({'status': 'success', 'message': 'Withdrawal requested!'})
    except UserItem.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Item unavailable.'})


@login_required
@require_POST
@ratelimit(key='user', rate='5/m', block=False)
def withdraw_items_batch(request):
    """Множественный вывод: принимает список item_id, создаёт одну пачку WithdrawRequest."""
    if getattr(request, 'limited', False):
        return JsonResponse({'status': 'error', 'message': 'Too many withdraw requests'}, status=429)

    raw_ids = request.POST.get('item_ids', '')
    try:
        item_ids = [int(x) for x in raw_ids.split(',') if x.strip().isdigit()]
    except Exception:
        item_ids = []

    if not item_ids:
        return JsonResponse({'status': 'error', 'message': 'No items selected'})
    if len(item_ids) > 20:
        return JsonResponse({'status': 'error', 'message': 'Too many items (max 20)'})

    created = []
    try:
        with transaction.atomic():
            items = list(UserItem.objects.select_for_update().filter(
                id__in=item_ids,
                owner_name__iexact=request.user.username,
                status='available',
            ))
            if not items:
                return JsonResponse({'status': 'error', 'message': 'No available items.'})

            # Сортируем по value desc — бот будет обрабатывать крупные первыми
            items.sort(key=lambda it: (-int(it.item_value or 0), it.item_name))

            for item in items:
                item.status = 'withdrawing'
                item.save(update_fields=['status'])
                WithdrawRequest.objects.create(
                    user_name=request.user.username,
                    item_name=item.item_name,
                    amount=item.amount,
                )
                log_item_action(request.user.username, 'withdraw_request', item=item, request=request)
                created.append(item)

            total_val = sum(int(it.item_value or 0) * int(it.amount or 1) for it in created)
            items_summary = '\n'.join(
                f'• {it.item_name} x{it.amount} ({it.item_value} SV)' for it in created[:10]
            )
            if len(created) > 10:
                items_summary += f'\n…and {len(created) - 10} more'
            send_trade_log(
                '📤 Batch Withdraw Request',
                f'**User:** {request.user.username}\n**Count:** {len(created)}\n**Total Value:** {total_val} SV\n\n{items_summary}',
                color=0xe74c3c,
            )
        return JsonResponse({'status': 'success', 'count': len(created)})
    except Exception as exc:
        logger.warning('withdraw_items_batch failed: %s', exc)
        return JsonResponse({'status': 'error', 'message': 'Batch withdraw failed'})


def api_check_withdraw(request):
    if not _bot_token_ok(request):
        return JsonResponse({'status': 'error', 'message': 'forbidden'}, status=403)
    username = request.GET.get('username')

    # Получаем ВСЕ активные заявки пользователя
    tasks = WithdrawRequest.objects.filter(user_name__iexact=username, is_completed=False)

    if tasks.exists():
        items_list = []
        for task in tasks:
            items_list.append({
                'item_name': task.item_name,
                'amount': task.amount,
                'task_id': task.id
            })

        # Отправляем список
        return JsonResponse({
            'found': True,
            'items': items_list
        })
    else:
        return JsonResponse({'found': False})


# 3. API ДЛЯ БОТА (ПОДТВЕРЖДЕНИЕ)
@csrf_exempt
def api_confirm_withdraw(request):
    if not _bot_token_ok(request):
        return JsonResponse({'status': 'error', 'message': 'forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error'})
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        with transaction.atomic():
            task = WithdrawRequest.objects.select_for_update().get(id=task_id)
            task.is_completed = True
            task.save(update_fields=['is_completed'])

            withdrawn = UserItem.objects.select_for_update().filter(
                owner_name__iexact=task.user_name,
                item_name=task.item_name,
                status='withdrawing',
            )
            for it in withdrawn:
                log_item_action(task.user_name, 'withdraw_confirmed', item=it,
                                note=f'task#{task.id}', request=request)
            withdrawn.delete()
        return JsonResponse({'status': 'success'})
    except Exception as exc:
        logger.warning("api_confirm_withdraw failed: %s", exc)
        return JsonResponse({'status': 'error'})


@login_required
@require_POST
def reset_all_withdrawals(request):
    if not request.user.is_superuser:
        return redirect('home')

    # 1. Находим все зависшие заявки
    pending_requests = WithdrawRequest.objects.filter(is_completed=False)

    # 2. Возвращаем предметы владельцам (меняем статус с 'withdrawing' на 'available')
    for req in pending_requests:
        UserItem.objects.filter(
            owner_name__iexact=req.user_name,
            item_name=req.item_name,
            status='withdrawing'
        ).update(status='available')

    # 3. Удаляем сами заявки
    count = pending_requests.count()
    pending_requests.delete()

    send_admin_log(
        '♻️ Reset All Withdrawals',
        f'**Admin:** {request.user.username}\n**Сброшено заявок:** {count}\nПредметы возвращены владельцам.',
        color=0xe67e22
    )

    messages.success(request, f"♻️ Сброшено {count} заявок! Предметы возвращены в инвентарь.")
    return redirect('home')


def convert_asset_to_url(roblox_asset_link):
    """
    Конвертация с отладкой.
    Только API. Если API не дало картинку -> возвращает дефолт.
    """
    DEFAULT_IMG = "https://static.wikia.nocookie.net/murder-mystery-2/images/5/53/Godly_Icon.png"

    if not roblox_asset_link:
        return DEFAULT_IMG

    try:
        link_str = str(roblox_asset_link).strip()

        # 0. Если это уже прямая ссылка на CDN
        if "rbxcdn.com" in link_str:
            return link_str.replace("http://", "https://")

        asset_id = None

        # 1. УНИВЕРСАЛЬНЫЙ ПОИСК ID
        # Ищем цифры после rbxassetid://, assetId= или id=
        match = re.search(r'(?:rbxassetid://|assetId=|id=)(\d+)', link_str, re.IGNORECASE)

        if match:
            asset_id = match.group(1)
        elif link_str.isdigit():
            asset_id = link_str

        # === ОТЛАДКА В КОНСОЛЬ ===
        print(f"🔍 [DEBUG] Входящая ссылка: {link_str}")
        print(f"🔍 [DEBUG] Найденный ID: {asset_id}")
        # =========================

        # Если ID так и не нашли
        if not asset_id:
            # Если это просто HTTP ссылка, вернем её
            if link_str.startswith("http"):
                return link_str
            return DEFAULT_IMG

        # 2. Пробуем официальный API
        try:
            url = f"https://thumbnails.roblox.com/v1/assets?assetIds={asset_id}&returnPolicy=PlaceHolder&size=420x420&format=Png"
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data and len(data['data']) > 0:
                    image_url = data['data'][0].get('imageUrl')
                    if image_url:
                        print(f"✅ [DEBUG] Картинка получена из API: {image_url}")
                        return image_url
        except Exception as api_error:
            print(f"⚠️ [DEBUG] Ошибка API Роблокса: {api_error}")
            pass

            # 3. ПУНКТ УБРАН (Фолбэк удален)
        # Если API не сработало, возвращаем дефолтную иконку
        print("❌ [DEBUG] API не вернул картинку, ставлю заглушку.")
        return DEFAULT_IMG

    except Exception as e:
        print(f"⚠️ [DEBUG] Общая ошибка функции: {e}")
        return DEFAULT_IMG


@login_required
def check_flip_status(request):
    """
    Проверяет, есть ли завершенные игры, анимацию которых игрок еще не видел.
    """
    user = request.user.username

    # Ищем игры, где пользователь участвовал, игра закончена, но он не видел результат
    # Для Player 1
    game_p1 = CoinflipGame.objects.filter(
        player1__iexact=user,
        is_active=False,
        player1_viewed=False
    ).first()

    # Для Player 2
    game_p2 = CoinflipGame.objects.filter(
        player2__iexact=user,
        is_active=False,
        player2_viewed=False
    ).first()

    game = game_p1 or game_p2

    if game:
        # Формируем данные для анимации
        data = {
            'found': True,
            'game_id': game.id,
            'player1': game.player1,
            'player2': game.player2,
            'winner': game.winner,
            'total_bet': game.value1 + game.value2,
            'creator_side': game.creator_side,  # 'green' или 'yellow'
            'result_code': game.random_result,  # 1 или 2
            'game_hash': game.game_hash or 'N/A',
        }
        return JsonResponse(data)

    return JsonResponse({'found': False})


@login_required
def mark_flip_viewed(request):
    """
    Помечает игру как просмотренную пользователем
    """
    if request.method == 'POST':
        game_id = request.POST.get('game_id')
        try:
            game = CoinflipGame.objects.get(id=game_id)
            if game.player1.lower() == request.user.username.lower():
                game.player1_viewed = True
            elif game.player2 and game.player2.lower() == request.user.username.lower():
                game.player2_viewed = True
            game.save()
            return JsonResponse({'status': 'ok'})
        except CoinflipGame.DoesNotExist:
            return JsonResponse({'status': 'error'})
    return JsonResponse({'status': 'error'})


def api_active_games_json(request):
    """Возвращает JSON со списком активных игр и их HTML"""
    active_games = CoinflipGame.objects.filter(is_active=True).order_by('-created_at')

    # Собираем аватарки (как в coinflip_home)
    players_set = set()
    for g in active_games:
        players_set.add(g.player1)
        if g.player2: players_set.add(g.player2)

    avatars = {}
    for p_name in players_set:
        avatars[p_name] = get_cached_avatar(p_name)

    games_data = []
    for game in active_games:
        # Рендерим HTML для каждой карточки прямо на сервере
        context = {
            'game': game,
            'user': request.user,
            'avatars': avatars,
        }
        # Используем созданный нами ранее includes/game_card.html
        html = render_to_string('includes/game_card.html', context, request=request)

        games_data.append({
            'id': game.id,
            'html': html
        })

    return JsonResponse({'games': games_data, 'online': _online_count_safe()})

@login_required
@require_POST
@ratelimit(key='user', rate='30/m', block=False)
def delete_item(request):
    if getattr(request, 'limited', False):
        return JsonResponse({'status': 'error', 'message': 'Too fast'}, status=429)
    item_id = request.POST.get('item_id')
    try:
        with transaction.atomic():
            item = UserItem.objects.select_for_update().get(
                id=item_id,
                owner_name__iexact=request.user.username,
                status='available',
            )
            log_item_action(request.user.username, 'delete', item=item, request=request)
            item.delete()
        return JsonResponse({'status': 'success'})
    except UserItem.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Item not found or currently in use (game/withdraw).',
        })

@csrf_exempt
def api_cancel_withdraw(request):
    if not _bot_token_ok(request):
        return JsonResponse({'status': 'error', 'message': 'forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error'})
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        with transaction.atomic():
            task = WithdrawRequest.objects.select_for_update().get(id=task_id)
            stuck = list(UserItem.objects.select_for_update().filter(
                owner_name__iexact=task.user_name,
                item_name=task.item_name,
                status='withdrawing',
            ))
            for it in stuck:
                it.status = 'available'
                it.save(update_fields=['status'])
                log_item_action(task.user_name, 'withdraw_cancelled', item=it,
                                note=f'task#{task.id}', request=request)
            task.delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.warning("api_cancel_withdraw failed: %s", e)
        return JsonResponse({'status': 'error'})


def get_cached_avatar(username):
    username = _normalize_username(username)
    if not username:
        return DEFAULT_AVATAR_URL

    cache_key = username.lower()
    if cache_key in AVATAR_CACHE:
        return AVATAR_CACHE[cache_key]

    if time.time() - AVATAR_NEGATIVE_CACHE.get(cache_key, 0) < AVATAR_NEGATIVE_TTL:
        return DEFAULT_AVATAR_URL

    url = get_roblox_avatar(username)
    if url and url != DEFAULT_AVATAR_URL:
        AVATAR_CACHE[cache_key] = url
        return url

    AVATAR_NEGATIVE_CACHE[cache_key] = time.time()
    return DEFAULT_AVATAR_URL


def api_get_avatar(request, username):
    """JSON API для ленивой загрузки Roblox аватарок"""
    url = get_cached_avatar(username)
    return JsonResponse({'url': url})


@login_required
@require_POST
@ratelimit(key='user', rate='5/10s', block=False)
@ratelimit(key='user', rate='30/m', block=False)
def send_chat_message(request):
    if getattr(request, 'limited', False):
        return JsonResponse({'status': 'error', 'message': 'Slow down — too many messages'}, status=429)
    try:
        data = json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Bad request'}, status=400)

    cleaned, err = validate_chat_message(request.user, data.get('message', ''))
    if err:
        return JsonResponse({'status': 'error', 'message': err}, status=400)

    ChatMessage.objects.create(user=request.user, message=cleaned)
    return JsonResponse({'status': 'success'})


# views.py

def get_chat_messages(request):
    # Берем последние 50 сообщений
    msgs = ChatMessage.objects.select_related('user').order_by('-created_at')[:50]

    # Получаем все префиксы пользователей из этих сообщений
    user_ids = set(msg.user_id for msg in msgs)
    prefixes = {p.user_id: p for p in UserChatPrefix.objects.filter(user_id__in=user_ids)}

    data = []
    # Разворачиваем (старые сверху)
    for msg in reversed(msgs):
        is_me = (request.user.is_authenticated and msg.user == request.user)

        prefix_data = prefixes.get(msg.user_id)
        prefix_text = prefix_data.prefix if prefix_data and prefix_data.prefix else ''
        prefix_color = prefix_data.color if prefix_data and prefix_data.color else ''

        data.append({
            'id': msg.id,
            'user': msg.user.username,
            'avatar': get_cached_avatar(msg.user.username),
            'text': msg.message,
            'time': msg.created_at.strftime("%H:%M"),  # UTC, fallback
            'time_iso': msg.created_at.isoformat(),
            'is_me': is_me,
            'prefix': prefix_text,
            'prefix_color': prefix_color,
        })

    return JsonResponse({'messages': data})


# === CHAT PREFIX SYSTEM ===

CHAT_PREFIXES = [
    {'name': 'Rookie', 'required_games': 0, 'description': 'Available for everyone'},
    {'name': 'Gambler', 'required_games': 10, 'description': 'Play 10+ games'},
    {'name': 'Experienced', 'required_games': 50, 'description': 'Play 50+ games'},
    {'name': 'Legend', 'required_games': 100, 'description': 'Play 100+ games'},
    {'name': 'King', 'required_games': 200, 'description': 'Play 200+ games'},
    {'name': 'Immortal', 'required_games': 500, 'description': 'Play 500+ games'},
    {'name': 'Custom', 'required_games': 999999, 'description': 'Your own tag'},
]

CHAT_PREFIX_COLORS = [
    '#00ff9d', '#00e5ff', '#c084fc', '#fbbf24',
    '#ff6b6b', '#ff9f43', '#f368e0', '#0abde3',
    '#10dc60', '#ffffff',
]


def _get_user_games_count(username):
    """Считаем кол-во завершённых игр пользователя"""
    return CoinflipGame.objects.filter(
        Q(player1__iexact=username) | Q(player2__iexact=username),
        is_active=False
    ).count()


@login_required
def get_chat_prefixes(request):
    """Получить доступные префиксы + текущий выбранный + кол-во игр"""
    username = request.user.username
    games_count = _get_user_games_count(username)

    # Текущий префикс
    try:
        current = UserChatPrefix.objects.get(user=request.user)
        current_prefix = current.prefix
        current_color = current.color
    except UserChatPrefix.DoesNotExist:
        current_prefix = ''
        current_color = '#00ff9d'

    # Специальные пользователи с полным доступом ко всем префиксам
    FULL_PREFIX_ACCESS_USERS = ['woundwound']
    has_full_access = username.lower() in [u.lower() for u in FULL_PREFIX_ACCESS_USERS]

    prefixes = []
    for p in CHAT_PREFIXES:
        prefixes.append({
            'name': p['name'],
            'required_games': p['required_games'],
            'description': p['description'],
            'unlocked': has_full_access or games_count >= p['required_games'],
        })

    return JsonResponse({
        'status': 'ok',
        'games_count': games_count,
        'current_prefix': current_prefix,
        'current_color': current_color,
        'prefixes': prefixes,
        'colors': CHAT_PREFIX_COLORS,
    })


@login_required
def set_chat_prefix(request):
    """Установить префикс и цвет"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST only'})

    try:
        data = json.loads(request.body)
        prefix_name = data.get('prefix', '').strip()
        color = data.get('color', '#00ff9d').strip()
        custom_text = data.get('custom_text', '').strip()
    except:
        return JsonResponse({'status': 'error', 'message': 'Invalid data'})

    # Проверяем что цвет из списка
    if color not in CHAT_PREFIX_COLORS:
        return JsonResponse({'status': 'error', 'message': 'Invalid color'})

    # Если пустой - сброс
    if not prefix_name:
        UserChatPrefix.objects.filter(user=request.user).delete()
        return JsonResponse({'status': 'ok', 'prefix': '', 'color': ''})

    # Проверяем что префикс существует и разблокирован
    valid_prefix = None
    for p in CHAT_PREFIXES:
        if p['name'] == prefix_name:
            valid_prefix = p
            break

    if not valid_prefix:
        return JsonResponse({'status': 'error', 'message': 'Invalid prefix'})

    games_count = _get_user_games_count(request.user.username)
    FULL_PREFIX_ACCESS_USERS = ['woundwound']
    has_full_access = request.user.username.lower() in [u.lower() for u in FULL_PREFIX_ACCESS_USERS]
    if not has_full_access and games_count < valid_prefix['required_games']:
        return JsonResponse({'status': 'error', 'message': f'Need {valid_prefix["required_games"]}+ games'})

    # Для Custom — используем пользовательский текст
    if prefix_name == 'Custom':
        if not custom_text:
            return JsonResponse({'status': 'error', 'message': 'Enter your custom tag'})
        if len(custom_text) > 16:
            return JsonResponse({'status': 'error', 'message': 'Max 16 characters'})
        # Сохраняем пользовательский текст вместо "Custom"
        save_prefix = custom_text
    else:
        save_prefix = prefix_name

    # Сохраняем
    obj, created = UserChatPrefix.objects.update_or_create(
        user=request.user,
        defaults={'prefix': save_prefix, 'color': color}
    )

    return JsonResponse({'status': 'ok', 'prefix': save_prefix, 'color': color})


# === USER STATS API ===
def api_user_stats(request):
    username = request.GET.get('username', '').strip()
    period = request.GET.get('period', 'all')

    if not username:
        return JsonResponse({'status': 'error', 'message': 'No username'})

    # Avatar
    avatar = get_cached_avatar(username)

    # Time filter
    now = timezone.now()
    date_filter = None
    if period == 'today':
        date_filter = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == '7d':
        date_filter = now - timezone.timedelta(days=7)
    elif period == '30d':
        date_filter = now - timezone.timedelta(days=30)

    # Get all finished games for this user
    games_qs = CoinflipGame.objects.filter(
        Q(player1__iexact=username) | Q(player2__iexact=username),
        is_active=False
    )

    if date_filter:
        games_qs = games_qs.filter(created_at__gte=date_filter)

    games_qs = games_qs.order_by('-created_at')

    # Calculate stats
    total_profit = 0
    wins = 0
    losses = 0
    history = []

    # Collect opponent usernames for batch avatar fetch
    opponent_names = set()
    for g in games_qs:
        if g.player1.lower() == username.lower():
            if g.player2:
                opponent_names.add(g.player2)
        else:
            opponent_names.add(g.player1)

    # Batch fetch opponent avatars
    opp_avatars = {}
    for opp in opponent_names:
        opp_avatars[opp] = get_cached_avatar(opp)

    for g in games_qs:
        is_player1 = (g.player1.lower() == username.lower())
        opponent = g.player2 if is_player1 else g.player1
        my_value = g.value1 if is_player1 else g.value2
        opp_value = g.value2 if is_player1 else g.value1
        won = (g.winner and g.winner.lower() == username.lower())

        if won:
            total_profit += opp_value
            wins += 1
        else:
            total_profit -= my_value
            losses += 1

        # Determine winning color
        if g.winner:
            winner_is_p1 = (g.winner.lower() == g.player1.lower())
            winning_color = g.creator_side if winner_is_p1 else ('yellow' if g.creator_side == 'green' else 'green')
        else:
            winning_color = 'green'

        history.append({
            'won': won,
            'opponent': opponent or '???',
            'opponent_avatar': opp_avatars.get(opponent, '') if opponent else '',
            'winning_color': winning_color,
            'value_change': opp_value if won else -my_value,
            'date': g.created_at.strftime('%d %b %Y, %H:%M'),
        })

    games_played = wins + losses
    win_rate = round((wins / games_played * 100), 1) if games_played > 0 else 0

    return JsonResponse({
        'status': 'ok',
        'username': username,
        'avatar': avatar,
        'total_profit': total_profit,
        'games_played': games_played,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'history': history[:50],  # limit to last 50
    })


# ==========================================
# GIVEAWAY SYSTEM
# ==========================================

import datetime

def _resolve_expired_giveaways():
    """Автоматически определяет победителя для истёкших розыгрышей"""
    expired = Giveaway.objects.filter(is_active=True, ends_at__lte=timezone.now())
    for giveaway in expired:
        participants = giveaway.participants or []
        if participants:
            winner = secrets.choice(participants)
            giveaway.winner = winner
            # Выдаём предмет победителю
            UserItem.objects.create(
                owner_name=winner,
                item_name=giveaway.item_name,
                item_value=giveaway.item_value,
                image_url=giveaway.item_image,
                status='available'
            )
        else:
            # Никто не участвовал — возвращаем предмет создателю
            UserItem.objects.create(
                owner_name=giveaway.creator,
                item_name=giveaway.item_name,
                item_value=giveaway.item_value,
                image_url=giveaway.item_image,
                status='available'
            )
            giveaway.winner = None
        giveaway.is_active = False
        giveaway.save()


@login_required
@require_POST
@ratelimit(key='user', rate='5/m', block=False)
def create_giveaway(request):
    """Создает розыгрыш из предмета инвентаря (вызывается кнопкой GIVEAWAY)"""
    if getattr(request, 'limited', False):
        return JsonResponse({'status': 'error', 'message': 'Too many giveaways'}, status=429)
    item_id = request.POST.get('item_id')
    try:
        with transaction.atomic():
            # Lock the user row to serialize giveaway-creation for this user (prevents race past the >=3 limit)
            User.objects.select_for_update().filter(pk=request.user.pk).first()

            item = UserItem.objects.select_for_update().get(
                id=item_id,
                owner_name__iexact=request.user.username,
                status='available',
            )

            existing = Giveaway.objects.filter(creator__iexact=request.user.username, is_active=True).count()
            if existing >= 3:
                return JsonResponse({'status': 'error', 'message': 'You can have max 3 active giveaways!'})

            now = timezone.now()
            giveaway = Giveaway.objects.create(
                creator=request.user.username,
                item_id=item.id,
                item_name=item.item_name,
                item_value=item.item_value,
                item_image=item.image_url,
                participants=[],
                is_active=True,
                created_at=now,
                ends_at=now + datetime.timedelta(hours=24),
            )

            log_item_action(request.user.username, 'giveaway_create', item=item,
                            related_giveaway_id=giveaway.id, request=request)
            item.delete()

        return JsonResponse({'status': 'success', 'giveaway_id': giveaway.id})
    except UserItem.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Item not found or unavailable.'})


@login_required
@require_POST
@ratelimit(key='user', rate='15/m', block=False)
def join_giveaway(request):
    """Пользователь участвует в розыгрыше"""
    if getattr(request, 'limited', False):
        return JsonResponse({'status': 'error', 'message': 'Too many actions'}, status=429)
    try:
        data = json.loads(request.body)
        giveaway_id = data.get('giveaway_id')

        giveaway = Giveaway.objects.get(id=giveaway_id, is_active=True)

        username = request.user.username

        # Нельзя участвовать в своём розыгрыше
        if giveaway.creator.lower() == username.lower():
            return JsonResponse({'status': 'error', 'message': 'Cannot join your own giveaway!'})

        # Проверяем активность: играл ли пользователь за последние 24 часа
        twenty_four_hours_ago = timezone.now() - datetime.timedelta(hours=24)
        has_played = CoinflipGame.objects.filter(
            Q(player1__iexact=username) | Q(player2__iexact=username),
            created_at__gte=twenty_four_hours_ago,
            is_active=False
        ).exists()
        if not has_played:
            return JsonResponse({'status': 'error', 'message': 'You must play at least one game in the last 24 hours to join giveaways!'})

        # Уже участвует?
        participants = giveaway.participants or []
        if username.lower() in [p.lower() for p in participants]:
            return JsonResponse({'status': 'error', 'message': 'You already joined this giveaway!'})

        # Проверяем не истёк ли
        if giveaway.is_expired():
            _resolve_expired_giveaways()
            return JsonResponse({'status': 'error', 'message': 'This giveaway has ended!'})

        participants.append(username)
        giveaway.participants = participants
        giveaway.save()

        return JsonResponse({
            'status': 'success',
            'participants_count': len(participants)
        })
    except Giveaway.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Giveaway not found.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
@require_POST
def force_end_giveaway(request):
    """Force-end a giveaway early (creator or superuser only)"""
    try:
        data = json.loads(request.body)
        ga_id = data.get('giveaway_id')
        giveaway = Giveaway.objects.get(id=ga_id, is_active=True)

        # Only creator or superuser can force-end
        if giveaway.creator.lower() != request.user.username.lower() and not request.user.is_superuser:
            return JsonResponse({'status': 'error', 'message': 'Not authorized'})

        participants = giveaway.participants or []
        winner = None
        if participants:
            winner = secrets.choice(participants)
            giveaway.winner = winner
            UserItem.objects.create(
                owner_name=winner,
                item_name=giveaway.item_name,
                item_value=giveaway.item_value,
                image_url=giveaway.item_image,
                status='available'
            )
        else:
            UserItem.objects.create(
                owner_name=giveaway.creator,
                item_name=giveaway.item_name,
                item_value=giveaway.item_value,
                image_url=giveaway.item_image,
                status='available'
            )
            giveaway.winner = None

        giveaway.is_active = False
        giveaway.save()

        return JsonResponse({
            'status': 'success',
            'winner': winner,
            'had_participants': len(participants) > 0
        })
    except Giveaway.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Giveaway not found'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def api_active_giveaways(request):
    """API: Возвращает JSON со всеми активными розыгрышами"""
    _resolve_expired_giveaways()

    giveaways = Giveaway.objects.filter(is_active=True).order_by('-item_value')

    data = []
    for g in giveaways:
        data.append({
            'id': g.id,
            'creator': g.creator,
            'creator_avatar': get_cached_avatar(g.creator),
            'item_name': g.item_name,
            'item_value': g.item_value,
            'item_image': g.item_image,
            'participants_count': g.participants_count(),
            'time_left': g.time_left(),
            'ends_at': g.ends_at.isoformat(),
            'already_joined': (
                request.user.is_authenticated and
                request.user.username.lower() in [p.lower() for p in (g.participants or [])]
            ),
        })

    # Также возвращаем недавно завершённые (последние 5)
    finished = Giveaway.objects.filter(is_active=False, winner__isnull=False).order_by('-ends_at')[:5]
    finished_data = []
    for g in finished:
        finished_data.append({
            'id': g.id,
            'creator': g.creator,
            'item_name': g.item_name,
            'item_value': g.item_value,
            'item_image': g.item_image,
            'winner': g.winner,
            'winner_avatar': get_cached_avatar(g.winner) if g.winner else '',
            'participants_count': g.participants_count(),
        })

    return JsonResponse({
        'active': data,
        'finished': finished_data
    })


# ==========================================
# SEO: robots.txt & sitemap.xml
# ==========================================

def leaderboard(request):
    """Топ игроков по числу побед в коинфлипе (всё время + последние 7 дней)."""
    from collections import defaultdict
    import datetime as _dt

    finished = CoinflipGame.objects.filter(is_active=False, winner__isnull=False)

    def _build_top(qs, limit=20):
        stats = defaultdict(lambda: {
            'username': '', 'games': 0, 'wins': 0, 'won_value': 0, 'wagered': 0,
        })
        for g in qs.only('player1', 'player2', 'winner', 'value1', 'value2'):
            for who, val in ((g.player1, g.value1), (g.player2, g.value2)):
                if not who:
                    continue
                key = who.lower()
                if key in HIDDEN_USERNAMES:
                    continue
                s = stats[key]
                s['username'] = s['username'] or who
                s['games'] += 1
                s['wagered'] += val or 0
            if not g.winner:
                continue
            wkey = g.winner.lower()
            if wkey in HIDDEN_USERNAMES:
                continue
            stats[wkey]['username'] = stats[wkey]['username'] or g.winner
            stats[wkey]['wins'] += 1
            stats[wkey]['won_value'] += (g.value1 or 0) + (g.value2 or 0)

        rows = []
        for s in stats.values():
            if s['games'] == 0:
                continue
            s['win_rate'] = round(s['wins'] / s['games'] * 100, 1)
            s['profit'] = s['won_value'] - s['wagered']
            rows.append(s)
        rows.sort(key=lambda x: (x['won_value'], x['wins']), reverse=True)
        return rows[:limit]

    week_cutoff = timezone.now() - _dt.timedelta(days=7)
    top_all = _build_top(finished)
    top_week = _build_top(finished.filter(created_at__gte=week_cutoff))

    for row in top_all + top_week:
        row['avatar'] = get_cached_avatar(row['username'])

    context = {
        'periods': [('all', top_all), ('week', top_week)],
        'bots_data': get_bots_status(),
        'avatar_url': get_cached_avatar(request.user.username) if request.user.is_authenticated else None,
    }
    return render(request, 'leaderboard.html', context)


def robots_txt(request):
    """Serve robots.txt for search engine crawlers."""
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /admin-panel/",
        "Disallow: /api/",
        "Disallow: /trade-log/",
        "Disallow: /withdraw/",
        "Disallow: /reset-withdraws/",
        "",
        f"Sitemap: https://{request.get_host()}/sitemap.xml",
    ]
    from django.http import HttpResponse
    return HttpResponse("\n".join(lines), content_type="text/plain")


def sitemap_xml(request):
    """Serve sitemap.xml for search engines with real lastmod timestamps."""
    from django.http import HttpResponse
    host = f"https://{request.get_host()}"

    # Фиксированная дата релиза — lastmod для статичных страниц. Обновляй руками
    # при реальной правке контента, иначе Google перестанет доверять sitemap.
    SITE_LAUNCH = "2026-04-15"

    def _fmt(dt):
        return dt.strftime("%Y-%m-%d") if dt else SITE_LAUNCH

    # Реальные lastmod для страниц, зависящих от контента БД
    last_game = CoinflipGame.objects.order_by('-created_at').values_list('created_at', flat=True).first()
    last_giveaway = Giveaway.objects.order_by('-created_at').values_list('created_at', flat=True).first()
    home_last = max(filter(None, [last_game, last_giveaway]), default=None)

    urls = [
        {"loc": f"{host}/",            "priority": "1.0", "changefreq": "daily",   "lastmod": _fmt(home_last)},
        {"loc": f"{host}/coinflip/",   "priority": "0.9", "changefreq": "hourly",  "lastmod": _fmt(last_game)},
        {"loc": f"{host}/leaderboard/","priority": "0.8", "changefreq": "daily",   "lastmod": _fmt(last_game)},
        {"loc": f"{host}/trade/",      "priority": "0.6", "changefreq": "weekly",  "lastmod": SITE_LAUNCH},
        {"loc": f"{host}/login/",      "priority": "0.4", "changefreq": "yearly",  "lastmod": SITE_LAUNCH},
    ]
    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for u in urls:
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{u['loc']}</loc>")
        xml_lines.append(f"    <lastmod>{u['lastmod']}</lastmod>")
        xml_lines.append(f"    <changefreq>{u['changefreq']}</changefreq>")
        xml_lines.append(f"    <priority>{u['priority']}</priority>")
        xml_lines.append("  </url>")
    xml_lines.append("</urlset>")
    return HttpResponse("\n".join(xml_lines), content_type="application/xml")