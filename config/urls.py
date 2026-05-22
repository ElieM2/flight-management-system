from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),

    path("i18n/", include("django.conf.urls.i18n")),

    path("", include(("apps.dashboard.urls", "dashboard"), namespace="dashboard")),
    path("flights/", include(("apps.flights.urls", "flights"), namespace="flights")),
    path("airlines/", include(("apps.airlines.urls", "airlines"), namespace="airlines")),
    path("airports/", include(("apps.airports.urls", "airports"), namespace="airports")),
    path("aircraft/", include(("apps.aircraft.urls", "aircraft"), namespace="aircraft")),
    path("monitoring/", include(("apps.monitoring.urls", "monitoring"), namespace="monitoring")),
    path("sync/", include(("apps.integrations.urls", "integrations"), namespace="integrations")),
    path("analytics/", include(("apps.analytics.urls", "analytics"), namespace="analytics")),
    path("accounts/", include(("apps.accounts.urls", "accounts"), namespace="accounts")),
    path("copilot/", include(("apps.copilot.urls", "copilot"), namespace="copilot")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)