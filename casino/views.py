import requests
import json
import random
import secrets
import string
import hashlib
import re
import threading
import time
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.template.loader import render_to_string
from django.utils.timesince import timesince
from django.utils import timezone
from django.db.models import Sum, Q
from django.contrib.auth.models import User
from django.contrib import messages
from .models import *

# ==========================================
# 1. НАСТРОЙКИ И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================

# Впиши сюда реальные ники и ID твоих ботов
BOTS_CONFIG = [
    {'username': 'Bot_Trade_01', 'id': 5413661688},
    {'username': 'Bot_Trade_02', 'id': 5413661688},
]

AVATAR_CACHE = {}
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
    webhook_url = getattr(settings, 'DISCORD_WEBHOOK_URL', '')
    if not webhook_url:
        return

    # Предметы игроков
    p1_items = ', '.join([i.get('name', '?') for i in (game.items1 or [])])
    p2_items = ', '.join([i.get('name', '?') for i in (game.items2 or [])])
    total_value = (game.value1 or 0) + (game.value2 or 0)

    # Цвет embed — зелёный
    embed_color = 0x00ff9d

    # Кто выиграл
    winner_emoji = '🏆'
    loser = game.player2 if game.winner == game.player1 else game.player1

    # Random source
    random_source = 'Random.org' if game.random_result else 'N/A'

    embed = {
        'title': f'{winner_emoji} Coinflip Result — Game #{game.id}',
        'color': embed_color,
        'fields': [
            {
                'name': '🎲 Game Hash',
                'value': f'```{game.game_hash or "N/A"}```',
                'inline': False
            },
            {
                'name': '🟢 Player 1 (Creator)',
                'value': f'**{game.player1}**\n💰 {game.value1} SV\n🎮 {p1_items or "No items"}',
                'inline': True
            },
            {
                'name': '🟡 Player 2 (Joiner)',
                'value': f'**{game.player2}**\n💰 {game.value2} SV\n🎮 {p2_items or "No items"}',
                'inline': True
            },
            {
                'name': '\u200b',
                'value': '\u200b',
                'inline': False
            },
            {
                'name': f'{winner_emoji} Winner',
                'value': f'**{game.winner}**',
                'inline': True
            },
            {
                'name': '❌ Loser',
                'value': f'**{loser}**',
                'inline': True
            },
            {
                'name': '💰 Total Bet',
                'value': f'**{total_value} SV**',
                'inline': True
            },
            {
                'name': '🎰 Result Code',
                'value': f'`{game.random_result}` (1=Green, 2=Purple)',
                'inline': True
            },
            {
                'name': '🌐 Random Source',
                'value': random_source,
                'inline': True
            },
            {
                'name': '🕒 Played At',
                'value': f'<t:{int(game.created_at.timestamp())}:F>',
                'inline': True
            },
        ],
        'footer': {
            'text': f'MMFLIP • Provably Fair • Game #{game.id}',
        },
        'timestamp': game.created_at.isoformat(),
    }

    payload = {
        'username': 'MMFLIP Logs',
        'avatar_url': 'https://cdn-icons-png.flaticon.com/512/1001/1001371.png',
        'embeds': [embed]
    }

    try:
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception:
        pass  # Не блокируем игру из-за ошибки Discord


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
        ).order_by('-created_at')
        mode = 'user'

    context = {
        'logs': logs,
        'mode': mode,
        'bots_data': bots_data,
        'title': 'History',
        'avatar_url': avatar_url,
    }
    return render(request, 'trade.html', context)


# --- COINFLIP ГЛАВНАЯ ---
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
    }
    return render(request, 'coinflip.html', context)


# ==========================================
# 3. ИГРОВАЯ ЛОГИКА (CREATE, JOIN, CANCEL)
# ==========================================

@login_required
def create_game(request):
    if request.method == 'POST':

        last_game = CoinflipGame.objects.filter(
            player1=request.user.username
        ).order_by('-created_at').first()

        if last_game:
            # Считаем разницу во времени
            time_diff = (timezone.now() - last_game.created_at).total_seconds()
            if time_diff < 5:  # Если прошло меньше 5 секунд
                messages.error(request, "Please wait a few seconds before creating another game.")
                return redirect('coinflip')

        selected_ids = request.POST.getlist('items')
        side = request.POST.get('side', 'green')
        if side not in ['green', 'yellow']: side = 'green'

        if not selected_ids:
            messages.error(request, "Select items to bet!")
            return redirect('coinflip')

        items = UserItem.objects.filter(id__in=selected_ids, owner_name__iexact=request.user.username,
                                        status='available')
        total_bet = sum(item.item_value for item in items)

        if total_bet < 10:
            messages.error(request, "Minimum bet is 10 value.")
            return redirect('coinflip')

        items_json = []
        for item in items:
            item.status = 'betting'
            item.save()
            # Добавляем image_url в JSON
            items_json.append({
                'id': item.id,
                'name': item.item_name,
                'value': item.item_value,
                'image': item.image_url  # <---
            })

        CoinflipGame.objects.create(
            player1=request.user.username,
            items1=items_json,
            value1=total_bet,
            creator_side=side,
            is_active=True
        )
        messages.success(request, f"Game created on {side.upper()} side!")
        return redirect('coinflip')
    return redirect('coinflip')


@login_required
def join_game(request, game_id):
    if request.method == 'POST':
        # Проверяем, это AJAX запрос или обычный?
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        game = get_object_or_404(CoinflipGame, id=game_id)

        # --- ПРОВЕРКИ (Упростим для краткости, логика та же) ---
        error_msg = None
        if game.player1.lower() == request.user.username.lower():
            error_msg = "You cannot join your own game!"

        selected_ids = request.POST.getlist('items')
        if not selected_ids and not error_msg:
            error_msg = "Select items to match the bet!"

        if error_msg:
            if is_ajax: return JsonResponse({'status': 'error', 'message': error_msg})
            messages.error(request, error_msg)
            return redirect('coinflip')

        # Достаем предметы
        items = UserItem.objects.filter(id__in=selected_ids, owner_name__iexact=request.user.username,
                                        status='available')
        total_bet_p2 = sum(item.item_value for item in items)

        # Проверки ставок
        min_req = int(game.value1 * 0.8)
        max_req = int(game.value1 * 1.3)

        if total_bet_p2 < 10:
            error_msg = "Minimum bet is 10!"
        elif not (min_req <= total_bet_p2 <= max_req):
            error_msg = f"Bet out of range ({min_req}-{max_req})"

        if error_msg:
            if is_ajax: return JsonResponse({'status': 'error', 'message': error_msg})
            messages.error(request, error_msg)
            return redirect('coinflip')

        # === ЕСЛИ ВСЕ ОК, ИГРАЕМ ===

        # 1. Блокируем предметы
        items_json_p2 = []
        for item in items:
            item.status = 'betting'
            item.save()
            items_json_p2.append({
                'id': item.id, 'name': item.item_name, 'value': item.item_value, 'image': item.image_url
            })

        # 2. Определяем победителя
        try:
            resp = requests.get("https://www.random.org/integers/?num=1&min=1&max=2&col=1&base=10&format=plain&rnd=new",
                                timeout=3)
            result = int(resp.text.strip())
        except:
            result = secrets.randbelow(2) + 1

        winning_side_num = 1 if game.creator_side == 'green' else 2
        winner = game.player1 if result == winning_side_num else request.user.username

        # 2.5. Генерируем хеш игры для проверки честности
        game_hash = generate_game_hash(
            game.id, game.player1, request.user.username,
            result, settings.SECRET_KEY
        )

        # 3. Сохраняем игру
        game.player2 = request.user.username
        game.items2 = items_json_p2
        game.value2 = total_bet_p2
        game.winner = winner
        game.random_result = result
        game.game_hash = game_hash
        game.is_active = False  # Игра закончена
        game.save()

        # 4. Раздаем призы
        all_items_json = game.items1 + game.items2
        for i in all_items_json:
            try:
                db_item = UserItem.objects.get(id=i['id'])
                db_item.owner_name = winner
                db_item.status = 'available'
                db_item.save()
            except:
                pass

        # 5. Отправляем лог в Discord (асинхронно)
        send_discord_log_async(game)

        # === ГЛАВНОЕ ИЗМЕНЕНИЕ ===
        # Если запрос от JS -> возвращаем JSON, чтобы страница НЕ перезагружалась
        if is_ajax:
            return JsonResponse({'status': 'success'})

        # Для обычного входа (на всякий случай)
        return redirect('coinflip')

    return redirect('coinflip')


@login_required
def cancel_game(request, game_id):
    if request.method == 'POST':
        game = get_object_or_404(CoinflipGame, id=game_id)

        if game.player1 != request.user.username:
            return redirect('coinflip')
        if game.player2:
            return redirect('coinflip')

        for item_data in game.items1:
            try:
                db_item = UserItem.objects.get(id=item_data['id'])
                if db_item.owner_name == request.user.username:
                    db_item.status = 'available'
                    db_item.save()
            except UserItem.DoesNotExist:
                pass

        game.delete()
        messages.success(request, "Game cancelled.")
    return redirect('coinflip')


# ==========================================
# 4. ADMIN & AUTH & API
# ==========================================

@login_required
def add_test_item(request):
    if not request.user.is_superuser:
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


def admin_panel(request):
    """Admin panel for superusers to manage items & inventory"""
    if not request.user.is_authenticated or not request.user.is_superuser:
        return redirect('home')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_item':
            owner = request.POST.get('owner_name', request.user.username)
            item_name = request.POST.get('item_name', 'Currency')
            try:
                item_value = int(request.POST.get('item_value', 0))
            except (ValueError, TypeError):
                item_value = 0
            try:
                amount = int(request.POST.get('amount', 1))
            except (ValueError, TypeError):
                amount = 1
            image_url = request.POST.get('image_url', '')

            UserItem.objects.create(
                owner_name=owner,
                item_name=item_name,
                item_value=item_value,
                amount=amount,
                image_url=image_url,
                status='available'
            )
            messages.success(request, f'Added "{item_name}" (x{amount}, {item_value} SV) to {owner}')

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

        elif action == 'delete_item':
            item_id = request.POST.get('item_id')
            try:
                item = UserItem.objects.get(id=item_id)
                item.delete()
                messages.success(request, f'Deleted item #{item_id}')
            except UserItem.DoesNotExist:
                messages.error(request, 'Item not found')

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

    return render(request, 'admin_panel.html', {
        'inventory': inventory,
        'total_value': total_value,
        'presets': presets,
        'bots_data': bots_data,
        'avatar_url': avatar_url,
    })


@csrf_exempt
def accept_trade_log(request):
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

                    # Конвертируем ссылку (с защитой от ошибок)
                    clean_image_url = convert_asset_to_url(raw_image)
                    if not clean_image_url:
                        clean_image_url = "https://static.wikia.nocookie.net/murder-mystery-2/images/5/53/Godly_Icon.png"

                    # Создаем QTY карточек
                    for _ in range(qty):
                        UserItem.objects.create(
                            owner_name=sender_name,
                            item_name=item['name'],
                            item_value=item.get('value', 0),
                            image_url=clean_image_url,
                            status='available'
                        )
                except Exception as e_item:
                    print(f"⚠️ Ошибка с предметом {item.get('name')}: {e_item}")
                    continue  # Пропускаем битый предмет, но сохраняем остальные

            print("✅ Депозит успешно сохранен!")
            return JsonResponse({'status': 'success'})

        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА ДЕПОЗИТА: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error'}, status=405)


# views.py

# ... (импорты и другие функции остаются без изменений) ...

# === НОВАЯ ЛОГИКА АВТОРИЗАЦИИ (JSON) ===

@csrf_exempt
def robox_login(request):
    """Шаг 1: Принимаем ник, находим ID, генерируем код"""
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
            random_code = "DELTA-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

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


@csrf_exempt
def robox_login(request):
    """Шаг 1: Принимаем ник, находим ID, генерируем код"""
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
            random_code = "DELTA-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

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


@csrf_exempt
def verify_page(request):
    """Шаг 2: Проверяем код в описании"""
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
                login(request, user)

                # Чистим сессию
                del request.session['auth_code']

                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Code not found in bio! Wait 10s and try again.'
                })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'})


def logout_user(request):
    logout(request)
    return redirect('home')


@login_required
@require_POST
def withdraw_item(request):
    item_id = request.POST.get('item_id')
    try:
        item = UserItem.objects.get(id=item_id, owner_name=request.user.username, status='available')
        item.status = 'withdrawing'
        item.save()

        WithdrawRequest.objects.create(
            user_name=request.user.username,
            item_name=item.item_name,
            amount=item.amount  # Передаем количество в заявку
        )
        return JsonResponse({'status': 'success', 'message': 'Withdrawal requested!'})
    except UserItem.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Item unavailable.'})


def api_check_withdraw(request):
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
    if request.method == 'POST':
        data = json.loads(request.body)
        task_id = data.get('task_id')

        try:
            task = WithdrawRequest.objects.get(id=task_id)
            task.is_completed = True
            task.save()

            # Удаляем предмет из инвентаря сайта (он ушел в игру)
            # Или помечаем как 'withdrawn' для истории
            UserItem.objects.filter(
                owner_name__iexact=task.user_name,
                item_name=task.item_name,
                status='withdrawing'
            ).delete()  # Удаляем, так как пользователь забрал вещь

            return JsonResponse({'status': 'success'})
        except:
            return JsonResponse({'status': 'error'})


@login_required
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
@csrf_exempt
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

    return JsonResponse({'games': games_data})

@login_required
@require_POST
def delete_item(request):
    item_id = request.POST.get('item_id')
    try:
        item = UserItem.objects.get(
            id=item_id,
            owner_name=request.user.username,
            status='available'
        )
        item.delete()
        return JsonResponse({'status': 'success'})
    except UserItem.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Item not found or currently in use (game/withdraw).'
        })

@csrf_exempt
def api_cancel_withdraw(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            task_id = data.get('task_id')

            # Находим заявку
            task = WithdrawRequest.objects.get(id=task_id)

            # 1. Возвращаем предмету статус 'available' (чтобы юзер видел, что вывод не удался)
            # Если хочешь, чтобы предмет ИСЧЕЗ СОВСЕМ, удали этот блок UserItem...update
            UserItem.objects.filter(
                owner_name__iexact=task.user_name,
                item_name=task.item_name,
                status='withdrawing'
            ).update(status='available')

            # 2. Удаляем заявку, чтобы бот больше её не видел
            task.delete()

            print(f"🚫 Заявка {task_id} отменена (предмет не найден у бота)")
            return JsonResponse({'status': 'success'})
        except Exception as e:
            print(f"Error cancelling: {e}")
            return JsonResponse({'status': 'error'})
    return JsonResponse({'status': 'error'})


def get_cached_avatar(username):
    username = _normalize_username(username)
    if not username:
        return DEFAULT_AVATAR_URL

    cache_key = username.lower()
    if cache_key in AVATAR_CACHE:
        return AVATAR_CACHE[cache_key]

    # Если нет в кэше, пробуем достать
    url = get_roblox_avatar(username)
    if url:
        AVATAR_CACHE[cache_key] = url
        return url
    return DEFAULT_AVATAR_URL


def api_get_avatar(request, username):
    """JSON API для ленивой загрузки Roblox аватарок"""
    url = get_cached_avatar(username)
    return JsonResponse({'url': url})


@login_required
@csrf_exempt
def send_chat_message(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            msg_text = data.get('message', '').strip()

            if msg_text:
                ChatMessage.objects.create(user=request.user, message=msg_text)
                return JsonResponse({'status': 'success'})
        except:
            pass
    return JsonResponse({'status': 'error'})


# views.py

def get_chat_messages(request):
    # Берем последние 50 сообщений
    msgs = ChatMessage.objects.select_related('user').order_by('-created_at')[:50]

    data = []
    # Разворачиваем (старые сверху)
    for msg in reversed(msgs):
        is_me = (request.user.is_authenticated and msg.user == request.user)

        data.append({
            'id': msg.id,  # <--- ВАЖНО: Добавили ID для проверки
            'user': msg.user.username,
            'avatar': get_cached_avatar(msg.user.username),
            'text': msg.message,
            'time': msg.created_at.strftime("%H:%M"),
            'is_me': is_me
        })

    return JsonResponse({'messages': data})


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
@csrf_exempt
def create_giveaway(request):
    """Создает розыгрыш из предмета инвентаря (вызывается кнопкой GIVEAWAY)"""
    item_id = request.POST.get('item_id')
    try:
        item = UserItem.objects.get(
            id=item_id,
            owner_name__iexact=request.user.username,
            status='available'
        )

        # Проверяем — уже есть активный розыгрыш от этого юзера?
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
            ends_at=now + datetime.timedelta(hours=24)
        )

        # Убираем предмет из инвентаря
        item.delete()

        return JsonResponse({'status': 'success', 'giveaway_id': giveaway.id})
    except UserItem.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Item not found or unavailable.'})


@login_required
@require_POST
@csrf_exempt
def join_giveaway(request):
    """Пользователь участвует в розыгрыше"""
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