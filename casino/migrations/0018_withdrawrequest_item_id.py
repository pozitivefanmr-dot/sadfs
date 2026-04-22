from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('casino', '0017_itemlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='withdrawrequest',
            name='item_id',
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
    ]
