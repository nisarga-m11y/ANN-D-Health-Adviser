from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

admin.site.site_header = "ANN-D Administration"
admin.site.site_title = "ANN-D Admin"
admin.site.index_title = "ANN-D Admin Panel"

urlpatterns = [
    path("", lambda request: JsonResponse({"status": "ok", "service": "ANN-D backend"})),
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/chat/", include("apps.chatbot.urls")),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
