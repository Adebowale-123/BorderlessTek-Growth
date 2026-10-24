from django.contrib import admin

from .models import Lead, LeadEvent


class EventInline(admin.TabularInline):
    model = LeadEvent
    extra = 0


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("parent_name", "channel", "stage", "child_age", "next_follow_up", "updated_at")
    list_filter = ("stage", "channel")
    search_fields = ("parent_name", "email", "notes")
    inlines = [EventInline]
