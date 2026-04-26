from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('casino', '0019_chatmessage_reply_to'),
    ]

    operations = [
        migrations.AlterField(
            model_name='itemlog',
            name='action',
            field=models.CharField(choices=[
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
                ('tip_sent', 'Tip sent'),
                ('tip_received', 'Tip received'),
                ('delete', 'Deleted by user'),
                ('admin_delete', 'Deleted by admin'),
            ], db_index=True, max_length=32),
        ),
    ]
