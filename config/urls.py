from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from core.views import health

urlpatterns = [path("django-admin/", admin.site.urls), path("api/", include("api.urls")), path("", include("core.urls")), path("", include("dashboard.urls")), path("accounts/", include("accounts.urls")), path("appointments/", include("appointments.urls")), path("records/", include("medical_records.urls")), path("notifications/", include("notifications.urls")), path("reviews/", include("reviews.urls")), path("health/", health, name="health")]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "core.views.page_not_found"
handler500 = "core.views.server_error"
