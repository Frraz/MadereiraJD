from django.urls import path
from . import views

app_name = 'cadastros'

urlpatterns = [
    # ---------------------- Clientes ----------------------
    path('clientes/', views.ClienteListView.as_view(), name='cliente_list'),
    path('clientes/novo/', views.ClienteCreateView.as_view(), name='cliente_create'),
    path('clientes/<int:pk>/editar/', views.ClienteUpdateView.as_view(), name='cliente_update'),
    path('clientes/<int:pk>/excluir/', views.ClienteDeleteView.as_view(), name='cliente_delete'),

    # ----------------- Tipos de Madeira -------------------
    path('tipos_madeira/', views.TipoMadeiraListView.as_view(), name='tipo_madeira_list'),
    path('tipos_madeira/novo/', views.TipoMadeiraCreateView.as_view(), name='tipo_madeira_create'),
    path('tipos_madeira/<int:pk>/editar/', views.TipoMadeiraUpdateView.as_view(), name='tipo_madeira_update'),
    path('tipos_madeira/<int:pk>/excluir/', views.TipoMadeiraDeleteView.as_view(), name='tipo_madeira_delete'),

    # --------------------- Motoristas ---------------------
    path('motoristas/', views.MotoristaListView.as_view(), name='motorista_list'),
    path('motoristas/novo/', views.MotoristaCreateView.as_view(), name='motorista_create'),
    path('motoristas/<int:pk>/editar/', views.MotoristaUpdateView.as_view(), name='motorista_update'),
    path('motoristas/<int:pk>/excluir/', views.MotoristaDeleteView.as_view(), name='motorista_delete'),

    # -------------- Operadores / Usuários -----------------
    path('usuarios/', views.UsuarioListView.as_view(), name='usuario_list'),
    path('usuarios/novo/', views.UsuarioCreateView.as_view(), name='usuario_create'),
    path('usuarios/<int:pk>/editar/', views.UsuarioUpdateView.as_view(), name='usuario_edit'),
    # Se quiser permitir exclusão de usuários
    # path('usuarios/<int:pk>/excluir/', views.UsuarioDeleteView.as_view(), name='usuario_delete'),
]