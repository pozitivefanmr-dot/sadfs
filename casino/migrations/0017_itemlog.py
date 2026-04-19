import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('casino', '0016_commissionlog'),
    ]

    operations = [
        migrations.CreateModel(
            name='ItemLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(db_index=True, max_length=100)),
                ('action', models.CharField(choices=[
                    ('create', 'Created'),
                    ('bet_lock', 'Locked for bet'),
                    ('bet_unlock', 'Unlocked from bet'),
                    ('won', 'Won in coinflip'),
                    ('lost', 'Lost in coinflip'),
                    ('commission', 'Taken as commission'),
                    ('withdraw_request', 'Withdraw requested'),
                    ('withdraw_confirmed', 'Withdraw confirmed'),
                    ('withdraw_cancelled', 'Withdraw cancelled'),
                    ('giveaway_create', 'Sent to giveaway'),
                    ('giveaway_won', 'Won in giveaway'),
                    ('delete', 'Deleted by user'),
                    ('admin_delete', 'Deleted by admin'),
                ], db_index=True, max_length=32)),
                ('item_id', models.IntegerField(blank=True, null=True)),
                ('item_name', models.CharField(default='', max_length=100)),
                ('item_value', models.IntegerField(default=0)),
                ('related_game_id', models.IntegerField(blank=True, null=True)),
                ('related_giveaway_id', models.IntegerField(blank=True, null=True)),
                ('note', models.CharField(blank=True, default='', max_length=255)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['username', '-created_at'], name='casino_item_usernam_idx'),
                    models.Index(fields=['action', '-created_at'], name='casino_item_action_idx'),
                ],
            },
        ),
    ]
