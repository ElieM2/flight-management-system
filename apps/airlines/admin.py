from django.contrib import admin
from django.utils.html import format_html

from .models import Airline


@admin.register(Airline)
class AirlineAdmin(admin.ModelAdmin):
    list_display = (
        "logo_preview",
        "name",
        "iata_code",
        "icao_code",
        "country",
        "country_code",
        "flag_preview",
        "is_active",
        "updated_at",
    )

    search_fields = (
        "name",
        "iata_code",
        "icao_code",
        "country",
        "country_code",
    )

    list_filter = (
        "is_active",
        "country",
        "country_code",
    )

    readonly_fields = (
        "logo_preview",
        "flag_preview",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Airline identity",
            {
                "fields": (
                    "name",
                    "iata_code",
                    "icao_code",
                    "country",
                    "country_code",
                    "logo",
                    "logo_preview",
                    "flag_preview",
                )
            },
        ),
        (
            "Operational status",
            {
                "fields": (
                    "is_active",
                )
            },
        ),
        (
            "System information",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="width:44px;height:44px;object-fit:contain;border-radius:10px;background:#fff;border:1px solid #ddd;padding:4px;" />',
                obj.logo.url,
            )

        return format_html(
            '<span style="display:inline-flex;width:44px;height:44px;align-items:center;justify-content:center;border-radius:10px;background:#eff6ff;color:#2563eb;font-weight:800;border:1px solid #dbeafe;">{}</span>',
            obj.logo_initials,
        )

    def flag_preview(self, obj):
        if not obj.country_code:
            return "—"

        return format_html(
            '<img src="https://flagcdn.com/w40/{}.png" style="width:28px;height:20px;object-fit:cover;border-radius:4px;border:1px solid #ddd;" />',
            obj.country_code.lower(),
        )

    logo_preview.short_description = "Logo"
    flag_preview.short_description = "Flag"