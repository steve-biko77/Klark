from django.db import migrations

# Sources choisies pour leur flux RSS habituellement stable et détectable
# automatiquement (cf. detect_feed_urls) — à vérifier ponctuellement par un
# humain, un flux RSS peut être déplacé ou fermé par l'éditeur avec le temps.
PACKS = [
    {
        'name': 'Trader Finance',
        'description': "Actualité marchés, crypto et finance pour suivre l'ouverture des marchés.",
        'persona': 'TRADER',
        'sources': [
            {'name': 'CoinDesk', 'url': 'https://www.coindesk.com'},
            {'name': 'MarketWatch', 'url': 'https://www.marketwatch.com'},
            {'name': 'Investing.com', 'url': 'https://www.investing.com'},
        ],
    },
    {
        'name': 'Créateur Tech & IA',
        'description': "Sources tech de référence pour inspirer du contenu sectoriel.",
        'persona': 'CREATEUR',
        'sources': [
            {'name': 'TechCrunch', 'url': 'https://techcrunch.com'},
            {'name': 'Ars Technica', 'url': 'https://arstechnica.com'},
            {'name': 'The Verge', 'url': 'https://www.theverge.com'},
        ],
    },
    {
        'name': 'Passionné Sport',
        'description': "L'essentiel de l'actualité sportive, tous sports confondus.",
        'persona': 'PASSIONNE',
        'sources': [
            {'name': "L'Équipe", 'url': 'https://www.lequipe.fr'},
            {'name': 'BBC Sport', 'url': 'https://www.bbc.com/sport'},
            {'name': 'Eurosport', 'url': 'https://www.eurosport.fr'},
        ],
    },
]


def seed_packs(apps, schema_editor):
    TopicPack = apps.get_model('sources', 'TopicPack')
    for pack in PACKS:
        TopicPack.objects.get_or_create(name=pack['name'], defaults=pack)


def remove_packs(apps, schema_editor):
    TopicPack = apps.get_model('sources', 'TopicPack')
    TopicPack.objects.filter(name__in=[p['name'] for p in PACKS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('sources', '0002_topicpack'),
    ]

    operations = [
        migrations.RunPython(seed_packs, remove_packs),
    ]
