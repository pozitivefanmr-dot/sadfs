"""
Management-команда для синхронизации данных между локальной (SQLite) и удалённой (PostgreSQL) БД.

Использование:
    # Скопировать данные из PostgreSQL (Railway) → SQLite (локальная)
    python manage.py syncdb --direction pull

    # Скопировать данные из SQLite (локальная) → PostgreSQL (Railway)
    python manage.py syncdb --direction push

    # Только определённые модели
    python manage.py syncdb --direction pull --models casino.CoinflipGame casino.UserItem

    # Без подтверждения (для скриптов)
    python manage.py syncdb --direction push --no-confirm

    # С включением auth.User и contenttypes (нужно для FK-зависимостей)
    python manage.py syncdb --direction push --include-auth
"""

import json
import tempfile
from io import StringIO

from django.apps import apps
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connections


class Command(BaseCommand):
    help = 'Синхронизация данных между локальной (SQLite) и удалённой (PostgreSQL) БД'

    def add_arguments(self, parser):
        parser.add_argument(
            '--direction',
            type=str,
            required=True,
            choices=['pull', 'push'],
            help=(
                'pull = скачать из Railway PostgreSQL → локальную SQLite; '
                'push = загрузить из локальной SQLite → Railway PostgreSQL'
            ),
        )
        parser.add_argument(
            '--models',
            nargs='*',
            type=str,
            help='Список моделей для синхронизации (формат: app.Model). По умолчанию — все модели casino.',
        )
        parser.add_argument(
            '--no-confirm',
            action='store_true',
            help='Пропустить подтверждение (для скриптов).',
        )
        parser.add_argument(
            '--flush-target',
            action='store_true',
            help='Очистить целевые таблицы перед загрузкой данных.',
        )
        parser.add_argument(
            '--include-auth',
            action='store_true',
            default=True,
            help='Включить auth.User и contenttypes (нужно для FK-зависимостей). По умолчанию: True.',
        )
        parser.add_argument(
            '--no-auth',
            action='store_true',
            help='НЕ включать auth.User и contenttypes.',
        )

    def _get_db_aliases(self, direction):
        """Определяет source и target базы данных по направлению."""
        db_settings = connections.databases

        if direction == 'pull':
            # pull: remote → local
            # Если default = PostgreSQL, source='default', target='local'
            # Если default = SQLite, source='remote', target='default'
            if 'remote' in db_settings:
                return 'remote', 'default'
            elif 'local' in db_settings:
                return 'default', 'local'
            else:
                raise CommandError(
                    'Не удалось определить базы данных для pull.\n'
                    'Убедитесь, что DATABASE_PUBLIC_URL задан в .env.\n'
                    'При USE_LOCAL_DB=true: default=SQLite, remote=PostgreSQL.\n'
                    'При USE_LOCAL_DB=false (или не задано): default=PostgreSQL, local=SQLite.'
                )
        else:
            # push: local → remote
            if 'remote' in db_settings:
                return 'default', 'remote'
            elif 'local' in db_settings:
                return 'local', 'default'
            else:
                raise CommandError(
                    'Не удалось определить базы данных для push.\n'
                    'Убедитесь, что DATABASE_PUBLIC_URL задан в .env.'
                )

    def _get_models(self, model_names, include_auth=True):
        """Получает список моделей для синхронизации."""
        # Модели, которые идут ПЕРЕД основными (FK-зависимости)
        pre_models = []
        if include_auth:
            pre_models = [ContentType, User]

        if model_names:
            models = []
            for name in model_names:
                try:
                    app_label, model_name = name.split('.')
                    model = apps.get_model(app_label, model_name)
                    models.append(model)
                except (ValueError, LookupError) as e:
                    raise CommandError(f'Модель "{name}" не найдена: {e}')
            # Добавляем pre_models только если их нет в списке
            for pm in pre_models:
                if pm not in models:
                    models.insert(0, pm)
            return models

        # По умолчанию — все модели из casino
        casino_models = list(apps.get_app_config('casino').get_models())
        # pre_models идут первыми
        result = []
        for pm in pre_models:
            if pm not in casino_models:
                result.append(pm)
        result.extend(casino_models)
        return result

    def _get_db_engine_name(self, alias):
        """Возвращает человекочитаемое имя движка БД."""
        engine = connections.databases[alias].get('ENGINE', '')
        if 'sqlite' in engine:
            return f'SQLite ({alias})'
        elif 'postgres' in engine:
            host = connections.databases[alias].get('HOST', 'unknown')
            name = connections.databases[alias].get('NAME', 'unknown')
            return f'PostgreSQL {name}@{host} ({alias})'
        return f'{engine} ({alias})'

    def handle(self, *args, **options):
        direction = options['direction']
        model_names = options.get('models')
        no_confirm = options.get('no_confirm', False)
        flush_target = options.get('flush_target', False)
        include_auth = not options.get('no_auth', False)

        # Определяем source и target
        source_alias, target_alias = self._get_db_aliases(direction)

        source_name = self._get_db_engine_name(source_alias)
        target_name = self._get_db_engine_name(target_alias)

        # Получаем модели
        models = self._get_models(model_names, include_auth=include_auth)
        model_labels = [f'{m._meta.app_label}.{m.__name__}' for m in models]

        self.stdout.write(self.style.WARNING(
            f'\n=== СИНХРОНИЗАЦИЯ БАЗ ДАННЫХ ===\n'
            f'Направление: {direction.upper()}\n'
            f'Источник:     {source_name}\n'
            f'Цель:         {target_name}\n'
            f'Модели:       {", ".join(model_labels)}\n'
            f'Очистка:      {"Да" if flush_target else "Нет"}\n'
        ))

        if not no_confirm:
            confirm = input('Продолжить? [y/N]: ').strip().lower()
            if confirm not in ('y', 'yes', 'д', 'да'):
                self.stdout.write(self.style.ERROR('Отменено.'))
                return

        # Шаг 1: Применяем миграции на target
        self.stdout.write(self.style.NOTICE('→ Применяю миграции на целевой БД...'))
        try:
            call_command('migrate', database=target_alias, verbosity=0, no_input=True)
            self.stdout.write(self.style.SUCCESS('  ✓ Миграции применены'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ⚠ Миграции: {e}'))

        # Шаг 2: Дамп данных из source
        total_objects = 0
        all_data = []

        for model in models:
            label = f'{model._meta.app_label}.{model._meta.model_name}'
            try:
                queryset = model.objects.using(source_alias).all()
                count = queryset.count()
                total_objects += count

                if count > 0:
                    data = serializers.serialize('json', queryset)
                    all_data.extend(json.loads(data))
                    self.stdout.write(f'  → {label}: {count} записей')
                else:
                    self.stdout.write(f'  → {label}: пусто')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠ {label}: {e}'))

        if total_objects == 0:
            self.stdout.write(self.style.WARNING('\nИсточник пуст — нечего синхронизировать.'))
            return

        self.stdout.write(self.style.NOTICE(f'\n→ Всего объектов: {total_objects}'))

        # Шаг 3: Очистка target (если запрошено)
        if flush_target:
            self.stdout.write(self.style.NOTICE('→ Очищаю целевые таблицы...'))
            for model in reversed(models):  # Обратный порядок для FK
                try:
                    deleted, _ = model.objects.using(target_alias).all().delete()
                    if deleted:
                        self.stdout.write(f'  → Удалено {deleted} из {model.__name__}')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  ⚠ {model.__name__}: {e}'))

        # Шаг 4: Загрузка данных в target
        self.stdout.write(self.style.NOTICE('→ Загружаю данные в целевую БД...'))

        json_str = json.dumps(all_data)

        try:
            saved = 0
            skipped = 0
            for obj in serializers.deserialize('json', json_str, using=target_alias):
                try:
                    obj.save(using=target_alias)
                    saved += 1
                except Exception as e:
                    skipped += 1
                    if options.get('verbosity', 1) >= 2:
                        self.stdout.write(self.style.WARNING(
                            f'  ⚠ Пропущен {obj.object.__class__.__name__} pk={obj.object.pk}: {e}'
                        ))

            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Синхронизация завершена!\n'
                f'   Сохранено: {saved}, пропущено: {skipped}\n'
                f'   {source_name} → {target_name}'
            ))

            # Шаг 5: Сброс PostgreSQL sequences (если target — PostgreSQL)
            target_engine = connections.databases[target_alias].get('ENGINE', '')
            if 'postgres' in target_engine:
                self._reset_sequences(target_alias, models)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Ошибка загрузки: {e}'))
            raise CommandError(f'Не удалось загрузить данные: {e}')

    def _reset_sequences(self, db_alias, models):
        """Сбрасывает PostgreSQL sequences после импорта данных с явными ID."""
        self.stdout.write(self.style.NOTICE('→ Сбрасываю PostgreSQL sequences...'))
        conn = connections[db_alias]
        with conn.cursor() as cursor:
            for model in models:
                table = model._meta.db_table
                try:
                    cursor.execute(
                        f"SELECT setval(pg_get_serial_sequence('{table}','id'), "
                        f"coalesce(max(id), 1), max(id) IS NOT null) FROM {table}"
                    )
                    val = cursor.fetchone()[0]
                    self.stdout.write(f'  → {table}: sequence → {val}')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  ⚠ {table}: {e}'))
