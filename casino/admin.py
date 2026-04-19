from django.contrib import admin
from .models import TradeLog, CommissionLog, ItemLog


@admin.register(TradeLog)
class TradeLogAdmin(admin.ModelAdmin):
    # МЫ ЗАМЕНИЛИ 'player_name' НА 'sender_name' и добавили 'bot_name'
    list_display = ('sender_name', 'bot_name', 'get_items_count', 'created_at')

    # Здесь тоже нужно использовать новые имена
    search_fields = ('sender_name', 'bot_name')
    list_filter = ('created_at',)

    def get_items_count(self, obj):
        return len(obj.items)

    get_items_count.short_description = "Кол-во предметов"


@admin.register(CommissionLog)
class CommissionLogAdmin(admin.ModelAdmin):
    list_display = ('game', 'winner', 'item_name', 'item_value', 'total_pot', 'actual_percent', 'created_at')
    search_fields = ('winner', 'item_name')
    list_filter = ('created_at',)
    readonly_fields = ('game', 'winner', 'item_name', 'item_value', 'item_id',
                       'total_pot', 'total_items', 'target_commission', 'actual_percent', 'created_at')


@admin.register(ItemLog)
class ItemLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'username', 'action', 'item_name', 'item_value',
                    'related_game_id', 'related_giveaway_id', 'ip_address')
    list_filter = ('action', 'created_at')
    search_fields = ('username', 'item_name', 'note', 'ip_address')
    readonly_fields = ('username', 'action', 'item_id', 'item_name', 'item_value',
                       'related_game_id', 'related_giveaway_id', 'note', 'ip_address', 'created_at')
    date_hierarchy = 'created_at'