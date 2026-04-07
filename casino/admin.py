from django.contrib import admin
from .models import TradeLog, CommissionLog


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