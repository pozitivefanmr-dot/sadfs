from django.contrib import admin
from .models import TradeLog


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