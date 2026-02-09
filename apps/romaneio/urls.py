from django.urls import path

from .views import (
    RomaneioListView,
    RomaneioCreateView,
    RomaneioUpdateView,
    RomaneioDetailView,
    RomaneioDeleteView,
    get_preco_madeira,
)

app_name = "romaneio"

urlpatterns = [
    path("", RomaneioListView.as_view(), name="romaneio_list"),
    path("novo/", RomaneioCreateView.as_view(), name="romaneio_create"),
    path("<int:pk>/", RomaneioDetailView.as_view(), name="romaneio_detail"),
    path("<int:pk>/editar/", RomaneioUpdateView.as_view(), name="romaneio_update"),
    path("excluir/<int:pk>/", RomaneioDeleteView.as_view(), name="romaneio_delete"),

    # API utilitária
    path("api/preco-madeira/", get_preco_madeira, name="get_preco_madeira"),
]
