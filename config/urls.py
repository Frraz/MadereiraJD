from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.core.auth_views import CustomPasswordResetView


urlpatterns = [
    path("admin/", admin.site.urls),

    # Auth (login/logout + reset de senha por e-mail)
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(template_name="registration/logged_out.html"),
        name="logout",
    ),

    path(
        "accounts/password_reset/",
        CustomPasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
            extra_email_context={
                "protocol": getattr(settings, "SITE_PROTOCOL", "http"),
            },
        ),
        name="password_reset",
    ),
    path(
        "accounts/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "accounts/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
        ),
        name="password_reset_confirm",
    ),
    path(
        "accounts/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),

    # Rotas principais
    path("", include(("apps.relatorios.urls", "relatorios"), namespace="relatorios")),
    path("cadastros/", include(("apps.cadastros.urls", "cadastros"), namespace="cadastros")),
    path("romaneio/", include(("apps.romaneio.urls", "romaneio"), namespace="romaneio")),
    path("financeiro/", include(("apps.financeiro.urls", "financeiro"), namespace="financeiro")),
    path("core/", include(("apps.core.urls", "core"), namespace="core")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)