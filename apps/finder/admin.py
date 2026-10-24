from django.contrib import admin

from .models import Opportunity, Source


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "community", "query", "is_active", "found_count", "last_checked", "last_error")
    list_filter = ("kind", "is_active")


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ("title", "score", "status", "community", "published_at")
    list_filter = ("status", "source")
    search_fields = ("title", "body", "author")
