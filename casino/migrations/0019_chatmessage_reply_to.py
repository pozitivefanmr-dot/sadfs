from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('casino', '0018_withdrawrequest_item_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='reply_to',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name='replies',
                to='casino.chatmessage',
            ),
        ),
    ]
