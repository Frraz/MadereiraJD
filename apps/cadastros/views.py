from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.db.models import Q, OuterRef, Subquery, Sum, Value, DecimalField, F
from django.db.models.functions import Coalesce
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from apps.financeiro.models import Pagamento
from apps.romaneio.models import Romaneio

from .forms import ClienteForm, TipoMadeiraForm, MotoristaForm
from .models import Cliente, TipoMadeira, Motorista
from django.db.models import ExpressionWrapper, DecimalField
from decimal import Decimal
from django.db.models import DecimalField, ExpressionWrapper, F, Subquery, Value
from django.db.models.functions import Coalesce


# ========== MIXINS ==========

class StaffRequiredMixin(UserPassesTestMixin):
    """Restringe o acesso a usuários staff (e opcionalmente superusers no queryset)."""

    def test_func(self):
        return self.request.user.is_staff


# ========== CLIENTES ==========

class ClienteListView(LoginRequiredMixin, ListView):
    model = Cliente
    template_name = "cadastros/cliente_list.html"
    context_object_name = "clientes"
    paginate_by = 20

    def get_queryset(self):
        busca = self.request.GET.get("q")
        ordenar = self.request.GET.get("ordenar", "nome")
        filtro_saldo = self.request.GET.get("saldo")

        qs = Cliente.objects.all()

        if busca:
            qs = qs.filter(nome__icontains=busca)

        pagamentos_sq = (
            Pagamento.objects.filter(cliente_id=OuterRef("pk"))
            .values("cliente_id")
            .annotate(total=Sum("valor"))
            .values("total")[:1]
        )

        vendas_sq = (
            Romaneio.objects.filter(cliente_id=OuterRef("pk"))
            .values("cliente_id")
            .annotate(total=Sum("valor_total"))
            .values("total")[:1]
        )

        qs = qs.annotate(
            total_pagamentos=Coalesce(
                Subquery(pagamentos_sq, output_field=DecimalField(max_digits=15, decimal_places=2)),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=15, decimal_places=2)
            ),
            total_vendas=Coalesce(
                Subquery(vendas_sq, output_field=DecimalField(max_digits=15, decimal_places=2)),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=15, decimal_places=2)
            )
        ).annotate(
            saldo_calc=ExpressionWrapper(
                F("total_pagamentos") - F("total_vendas"),
                output_field=DecimalField(max_digits=15, decimal_places=2)
            )
        )

        # Filtro por saldo
        if filtro_saldo == "negativos":
            qs = qs.filter(saldo_calc__lt=0)
        elif filtro_saldo == "positivos":
            qs = qs.filter(saldo_calc__gt=0)
        elif filtro_saldo == "zerados":
            qs = qs.filter(saldo_calc=0)

        # Ordenação
        if ordenar == "saldo":
            qs = qs.order_by("saldo_calc", "nome")
        elif ordenar == "saldo_desc":
            qs = qs.order_by("-saldo_calc", "nome")
        else:
            qs = qs.order_by("nome")

        return qs


class ClienteCreateView(LoginRequiredMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "cadastros/cliente_form.html"
    success_url = reverse_lazy("cadastros:cliente_list")

    def form_valid(self, form):
        messages.success(self.request, "Cliente cadastrado com sucesso!")
        return super().form_valid(form)


class ClienteUpdateView(LoginRequiredMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "cadastros/cliente_form.html"
    success_url = reverse_lazy("cadastros:cliente_list")

    def form_valid(self, form):
        messages.success(self.request, "Cliente atualizado com sucesso!")
        return super().form_valid(form)


class ClienteDeleteView(LoginRequiredMixin, DeleteView):
    model = Cliente
    template_name = "cadastros/cliente_confirm_delete.html"
    success_url = reverse_lazy("cadastros:cliente_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Cliente excluído com sucesso!")
        return super().delete(request, *args, **kwargs)


# ========== TIPOS DE MADEIRA ==========

class TipoMadeiraListView(LoginRequiredMixin, ListView):
    model = TipoMadeira
    template_name = "cadastros/tipo_madeira_list.html"
    context_object_name = "tipos_madeira"
    paginate_by = 30

    def get_queryset(self):
        queryset = super().get_queryset()
        busca = self.request.GET.get("q")
        if busca:
            queryset = queryset.filter(nome__icontains=busca)
        # Se desejar no futuro: queryset = queryset.filter(ativo=True)
        return queryset


class TipoMadeiraCreateView(LoginRequiredMixin, CreateView):
    model = TipoMadeira
    form_class = TipoMadeiraForm
    template_name = "cadastros/tipo_madeira_form.html"
    success_url = reverse_lazy("cadastros:tipo_madeira_list")

    def form_valid(self, form):
        messages.success(self.request, "Tipo de madeira cadastrado com sucesso!")
        return super().form_valid(form)


class TipoMadeiraUpdateView(LoginRequiredMixin, UpdateView):
    model = TipoMadeira
    form_class = TipoMadeiraForm
    template_name = "cadastros/tipo_madeira_form.html"
    success_url = reverse_lazy("cadastros:tipo_madeira_list")

    def form_valid(self, form):
        messages.success(self.request, "Tipo de madeira atualizado com sucesso!")
        return super().form_valid(form)


class TipoMadeiraDeleteView(LoginRequiredMixin, DeleteView):
    model = TipoMadeira
    template_name = "cadastros/tipo_madeira_confirm_delete.html"
    success_url = reverse_lazy("cadastros:tipo_madeira_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Tipo de madeira excluído com sucesso!")
        return super().delete(request, *args, **kwargs)


# ========== MOTORISTAS ==========

class MotoristaListView(LoginRequiredMixin, ListView):
    model = Motorista
    template_name = "cadastros/motorista_list.html"
    context_object_name = "motoristas"
    paginate_by = 20


class MotoristaCreateView(LoginRequiredMixin, CreateView):
    model = Motorista
    form_class = MotoristaForm
    template_name = "cadastros/motorista_form.html"
    success_url = reverse_lazy("cadastros:motorista_list")

    def form_valid(self, form):
        messages.success(self.request, "Motorista cadastrado com sucesso!")
        return super().form_valid(form)


class MotoristaUpdateView(LoginRequiredMixin, UpdateView):
    model = Motorista
    form_class = MotoristaForm
    template_name = "cadastros/motorista_form.html"
    success_url = reverse_lazy("cadastros:motorista_list")

    def form_valid(self, form):
        messages.success(self.request, "Motorista atualizado com sucesso!")
        return super().form_valid(form)


class MotoristaDeleteView(LoginRequiredMixin, DeleteView):
    model = Motorista
    template_name = "cadastros/motorista_confirm_delete.html"
    success_url = reverse_lazy("cadastros:motorista_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Motorista excluído com sucesso!")
        return super().delete(request, *args, **kwargs)


# ========== USUÁRIOS / OPERADORES ==========

class UserStaffForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active", "is_staff"]


class UserSuperForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active", "is_staff", "is_superuser"]


class UsuarioListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = User
    template_name = "cadastros/usuario_list.html"
    context_object_name = "usuarios"
    paginate_by = 20

    def get_queryset(self):
        qs = User.objects.order_by("username")
        if not self.request.user.is_superuser:
            qs = qs.filter(is_superuser=False)

        busca = self.request.GET.get("q")
        if busca:
            qs = qs.filter(
                Q(username__icontains=busca)
                | Q(first_name__icontains=busca)
                | Q(last_name__icontains=busca)
                | Q(email__icontains=busca)
            )
        return qs


class UsuarioCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = User
    template_name = "cadastros/usuario_form.html"
    success_url = reverse_lazy("cadastros:usuario_list")

    def get_form_class(self):
        return UserSuperForm if self.request.user.is_superuser else UserStaffForm

    def form_valid(self, form):
        # Define senha padrão na criação
        form.instance.set_password("123456")
        messages.success(self.request, "Usuário cadastrado com sucesso! (Senha padrão: 123456)")
        return super().form_valid(form)


class UsuarioUpdateView(LoginRequiredMixin, StaffRequiredMixin, UpdateView):
    model = User
    template_name = "cadastros/usuario_form.html"
    success_url = reverse_lazy("cadastros:usuario_list")

    def get_form_class(self):
        return UserSuperForm if self.request.user.is_superuser else UserStaffForm

    def form_valid(self, form):
        messages.success(self.request, "Usuário atualizado com sucesso!")
        return super().form_valid(form)