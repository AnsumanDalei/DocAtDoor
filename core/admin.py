from django.contrib import admin

from .models import ServiceEnquiry


@admin.register(ServiceEnquiry)
class ServiceEnquiryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "email", "service", "status")
    list_filter = ("status", "service", "created_at")
    search_fields = ("name", "email", "message")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    list_editable = ("status",)
    fieldsets = (
        ("Enquiry", {"fields": ("name", "email", "service", "message", "status", "created_at", "updated_at")}),
        ("Staff follow-up", {"fields": ("staff_notes",)}),
    )
