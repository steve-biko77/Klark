from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='scheduled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='post',
            name='status',
            field=models.TextField(
                choices=[
                    ('draft', 'Brouillon'),
                    ('scheduled', 'Planifié'),
                    ('published', 'Publié'),
                    ('failed', 'Échoué'),
                ],
                default='draft',
            ),
        ),
    ]
