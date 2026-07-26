from django.contrib import admin
from .models import Source, TopicPack

admin.site.register(Source)


@admin.register(TopicPack)
class TopicPackAdmin(admin.ModelAdmin):
    list_display = ['name', 'persona', 'is_active']
    list_filter = ['persona', 'is_active']
