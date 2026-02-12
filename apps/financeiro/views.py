from __future__ import annotations

from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.cadastros.models import Cliente

from .forms import PagamentoForm
from .models import Pagamento


class PagamentoListView(LoginRequiredMixin, ListView):
    model = Pagamento
    template_name = "financeiro/pagamento_list.html"
    context_object_name = "pagamentos"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("cliente")

        mes = self.request.GET.get("mes")
        ano = self.request.GET.get("ano")
        cliente_id = self.request.GET.get("cliente")

        # Limpa entradas (garante valores válidos inteiro)
        try:
            mes_int = int(mes) if mes else None
        except (TypeError, ValueError):
            mes_int = None
        try:
            ano_int = int(ano) if ano else None
        except (TypeError, ValueError):
            ano_int = None

        # Só filtra se usuário seleciona mês ou ano:
        if mes_int and ano_int:
            qs = qs.filter(data_pagamento__month=mes_int, data_pagamento__year=ano_int)
        elif ano_int:
            qs = qs.filter(data_pagamento__year=ano_int)
        elif mes_int:
            qs = qs.filter(data_pagamento__month=mes_int)
        # Se nenhum, mostra tudo

        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["clientes"] = Cliente.objects.filter(ativo=True).order_by("nome")

        # total do período em cima do queryset já filtrado/paginado pelo ListView
        context["total_periodo"] = self.object_list.aggregate(total=Sum("valor")).get("total") or 0

        return context


class PagamentoCreateView(LoginRequiredMixin, CreateView):
    model = Pagamento
    form_class = PagamentoForm
    template_name = "financeiro/pagamento_form.html"
    success_url = reverse_lazy("financeiro:pagamento_list")

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.usuario_cadastro = self.request.user
        self.object.save()

        messages.success(
            self.request,
            f"Pagamento de R$ {self.object.valor:.2f} cadastrado com sucesso! "
            f"Saldo atual do cliente: R$ {self.object.cliente.saldo_atual:.2f}"
        )
        return redirect(self.get_success_url())


class PagamentoUpdateView(LoginRequiredMixin, UpdateView):
    model = Pagamento
    form_class = PagamentoForm
    template_name = "financeiro/pagamento_form.html"
    success_url = reverse_lazy("financeiro:pagamento_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Pagamento atualizado com sucesso!")
        return response


class PagamentoDeleteView(LoginRequiredMixin, DeleteView):
    model = Pagamento
    template_name = "financeiro/pagamento_confirm_delete.html"
    success_url = reverse_lazy("financeiro:pagamento_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Pagamento excluído com sucesso!")
        return super().delete(request, *args, **kwargs)