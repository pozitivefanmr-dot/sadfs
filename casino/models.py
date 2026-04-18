from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class TradeLog(models.Model):
    # ... (оставь как было) ...
    sender_name = models.CharField(max_length=100, default="Unknown")
    bot_name = models.CharField(max_length=100, default="Bot")
    items = models.JSONField(default=list)
    created_at = models.DateTimeField(default=timezone.now)


class UserItem(models.Model):
    owner_name = models.CharField(max_length=100)
    item_name = models.CharField(max_length=100)
    item_value = models.IntegerField(default=0)
    amount = models.IntegerField(default=1)
    status = models.CharField(max_length=20, default='available')
    received_at = models.DateTimeField(default=timezone.now)
    image_url = models.CharField(max_length=500, default="", blank=True)


class CoinflipGame(models.Model):
    player1 = models.CharField(max_length=100)
    items1 = models.JSONField(default=list)
    # НОВОЕ ПОЛЕ: Сумма ставки Игрока 1
    value1 = models.IntegerField(default=0)

    creator_side = models.CharField(max_length=10, default='green')

    player2 = models.CharField(max_length=100, null=True, blank=True)
    items2 = models.JSONField(default=list)
    # НОВОЕ ПОЛЕ: Сумма ставки Игрока 2
    value2 = models.IntegerField(default=0)

    winner = models.CharField(max_length=100, null=True, blank=True)
    random_result = models.IntegerField(null=True, blank=True)
    game_hash = models.CharField(max_length=64, null=True, blank=True)  # SHA-256 hash
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    # Хелперы для диапазона
    @staticmethod
    def _round_step(value):
        """Определяет шаг округления в зависимости от величины"""
        if value < 20:
            return 5
        elif value < 100:
            return 5
        elif value < 500:
            return 25
        elif value < 2000:
            return 50
        elif value < 10000:
            return 100
        else:
            return 250

    def min_join_value(self):
        raw = int(self.value1 * 0.85)  # -15%
        step = self._round_step(raw)
        return max(1, (raw // step) * step)  # округление вниз

    def max_join_value(self):
        raw = int(self.value1 * 1.2)  # +20%
        step = self._round_step(raw)
        return ((raw + step - 1) // step) * step  # округление вверх

    player1_viewed = models.BooleanField(default=False)
    player2_viewed = models.BooleanField(default=False)


# В models.py добавь новую модель
class WithdrawRequest(models.Model):
    user_name = models.CharField(max_length=100)
    item_name = models.CharField(max_length=100)
    amount = models.IntegerField(default=1) # НОВОЕ ПОЛЕ: Сколько вывести
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)


# models.py

class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: {self.message[:20]}"


class UserChatPrefix(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_prefix')
    prefix = models.CharField(max_length=30, default='', blank=True)
    color = models.CharField(max_length=7, default='#00ff9d', blank=True)  # hex color

    def __str__(self):
        return f"{self.user.username}: ({self.prefix})"


class Giveaway(models.Model):
    creator = models.CharField(max_length=100)
    item_id = models.IntegerField()  # ID предмета UserItem
    item_name = models.CharField(max_length=100)
    item_value = models.IntegerField(default=0)
    item_image = models.CharField(max_length=500, default="", blank=True)
    participants = models.JSONField(default=list)  # Список ников участников
    winner = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField()  # created_at + 24h

    def participants_count(self):
        return len(self.participants)

    def time_left(self):
        """Возвращает оставшееся время в секундах"""
        delta = self.ends_at - timezone.now()
        return max(0, int(delta.total_seconds()))

    def is_expired(self):
        return timezone.now() >= self.ends_at

    def __str__(self):
        return f"Giveaway by {self.creator}: {self.item_name}"


class CommissionLog(models.Model):
    """Лог комиссий, снятых с выигрышей в coinflip"""
    game = models.ForeignKey(CoinflipGame, on_delete=models.CASCADE, related_name='commissions')
    winner = models.CharField(max_length=100)
    item_name = models.CharField(max_length=100)
    item_value = models.IntegerField(default=0)
    item_id = models.IntegerField()  # ID UserItem который забрали
    total_pot = models.IntegerField(default=0)  # Общая сумма ставки
    total_items = models.IntegerField(default=0)  # Общее кол-во предметов
    target_commission = models.FloatField(default=0)  # Целевая сумма комиссии (10%)
    actual_percent = models.FloatField(default=0)  # Фактический % комиссии
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Commission: {self.item_name} ({self.item_value}) from game #{self.game_id} | {self.actual_percent:.1f}%"