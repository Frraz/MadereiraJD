from __future__ import annotations

from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.cadastros.models import Cliente, TipoMadeira

from .forms import ItemRomaneioFormSet, RomaneioForm, UnidadeRomaneioFormSet
from .models import Romaneio


def build_tipos_madeira_json():
    """
    Retorna JSON com preços de madeiras ativas para popular o JS do formulário.
    """
    tipos_madeira = TipoMadeira.objects.filter(ativo=True).only("id", "preco_normal", "preco_com_frete")
    return {
        str(tm.id): {
            "normal": float(tm.preco_normal or 0),
            "com_frete": float(tm.preco_com_frete or 0),
        }
        for tm in tipos_madeira
    }


class RomaneioListView(LoginRequiredMixin, ListView):
    model = Romaneio
    template_name = "romaneio/romaneio_list.html"
    context_object_name = "romaneios"
    paginate_by = 20

    def get_queryset(self):
        qs = self.model.objects.select_related("cliente", "motorista").order_by("-data_romaneio", "-id")

        mes = self.request.GET.get("mes")
        ano = self.request.GET.get("ano")
        cliente_id = self.request.GET.get("cliente")
        numero = self.request.GET.get("numero")
        modalidade = self.request.GET.get("modalidade")

        if mes and ano:
            try:
                qs = qs.filter(data_romaneio__month=int(mes), data_romaneio__year=int(ano))
            except (ValueError, TypeError):
                pass
        else:
            now = datetime.now()
            qs = qs.filter(data_romaneio__month=now.month, data_romaneio__year=now.year)

        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)
        if numero:
            qs = qs.filter(numero_romaneio__icontains=numero)
        if modalidade:
            qs = qs.filter(modalidade=modalidade)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["clientes"] = Cliente.objects.filter(ativo=True).order_by("nome")

        totais = self.object_list.aggregate(total_m3=Sum("m3_total"), total_valor=Sum("valor_total"))
        context["total_m3_periodo"] = totais["total_m3"] or 0
        context["total_valor_periodo"] = totais["total_valor"] or 0

        anos = [d.year for d in Romaneio.objects.dates("data_romaneio", "year", order="ASC")]
        context["anos"] = anos or [datetime.now().year]
        context["meses"] = range(1, 13)
        context["modalidades"] = Romaneio.MODALIDADE_CHOICES
        return context


class _RomaneioFormsetsMixin:
    """
    Mixin para montar e injetar no context:
    - ItemRomaneioFormSet
    - UnidadeRomaneioFormSet por item (com prefixo estável: unidades-{index})
    - itens_com_unidades: lista de tuplas (item_form, unidade_formset)
    - tipos_madeira_json: JSON com preços
    """

    def _build_item_formset(self):
        """Constrói o formset de itens, com ou sem instance (create vs update)."""
        if self.request.POST:
            return ItemRomaneioFormSet(self.request.POST, instance=getattr(self, "object", None))
        return ItemRomaneioFormSet(instance=getattr(self, "object", None))

    def _build_unidades_formsets(self, formset):
        """
        Para cada form no formset de itens, cria um UnidadeRomaneioFormSet correspondente.
        Usa prefix estável: unidades-{index}.
        """
        unidades_formsets = []
        for i, item_form in enumerate(formset.forms):
            prefix = f"unidades-{i}"
            instance = item_form.instance if getattr(item_form.instance, "pk", None) else None

            if self.request.POST:
                uf = UnidadeRomaneioFormSet(self.request.POST, instance=instance, prefix=prefix)
            else:
                uf = UnidadeRomaneioFormSet(instance=instance, prefix=prefix)

            unidades_formsets.append(uf)
        return unidades_formsets

    def _inject_formsets_into_context(self, context, formset=None, unidades_formsets=None):
        """
        Injeta formsets no context.
        Se não fornecidos, constrói automaticamente.
        """
        if formset is None:
            formset = self._build_item_formset()
        if unidades_formsets is None:
            unidades_formsets = self._build_unidades_formsets(formset)

        context["formset"] = formset
        context["unidades_formsets"] = unidades_formsets
        context["itens_com_unidades"] = list(zip(formset.forms, unidades_formsets))
        context["tipos_madeira_json"] = build_tipos_madeira_json()
        return context


class _RomaneioSaveMixin:
    """
    Centraliza a lógica de salvar Romaneio + itens + unidades e recalcular totais.
    Evita duplicação entre Create e Update.
    """

    def _build_unidades_preview_for_create(self, request, formset):
        unidades_formsets_preview = []
        for i, _item_form in enumerate(formset.forms):
            prefix = f"unidades-{i}"
            unidades_formsets_preview.append(UnidadeRomaneioFormSet(request.POST, instance=None, prefix=prefix))
        return unidades_formsets_preview

    def _validate_detalhado_requires_units(self, form, unidades_formsets_preview):
        """
        Se modalidade == DETALHADO, cada item precisa ter pelo menos 1 unidade válida.
        Coloca o erro no próprio formset (non_form_errors) para o template exibir.
        """
        unidades_valid = True
        if form.is_valid() and form.cleaned_data.get("modalidade") == "DETALHADO":
            for uf in unidades_formsets_preview:
                valid_units = sum(
                    1
                    for f in uf.forms
                    if f.is_valid() and not f.cleaned_data.get("DELETE", False)
                )
                if valid_units == 0:
                    uf._non_form_errors.append(
                        "No modo DETALHADO, cada tipo de madeira deve ter pelo menos uma unidade."
                    )
                    unidades_valid = False
        return unidades_valid

    def _save_unidades_for_itens(self, request, itens):
        for i, item in enumerate(itens):
            prefix = f"unidades-{i}"
            uf = UnidadeRomaneioFormSet(request.POST, instance=item, prefix=prefix)
            if uf.is_valid():
                uf.save()

    def _recalcular_totais_apos_salvar(self, romaneio: Romaneio):
        """
        Recalcula itens e romaneio de forma determinística.

        - SIMPLES: item.atualizar_totais() usa quantidade_m3_total informada.
        - DETALHADO: item.atualizar_totais() soma unidades.
        """
        itens_db = romaneio.itens.all().prefetch_related("unidades")
        for item in itens_db:
            item.atualizar_totais(save=True, atualizar_romaneio=False)

        romaneio.atualizar_totais()


class RomaneioCreateView(LoginRequiredMixin, _RomaneioFormsetsMixin, _RomaneioSaveMixin, CreateView):
    model = Romaneio
    form_class = RomaneioForm
    template_name = "romaneio/romaneio_form.html"
    success_url = reverse_lazy("romaneio:romaneio_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return self._inject_formsets_into_context(context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()

        # ancorar o inline formset numa instância (mesmo não salva ainda)
        self.object = Romaneio()
        formset = ItemRomaneioFormSet(request.POST, instance=self.object)

        unidades_formsets_preview = self._build_unidades_preview_for_create(request, formset)

        form_valid = form.is_valid()
        formset_valid = formset.is_valid()
        unidades_valid = all(uf.is_valid() for uf in unidades_formsets_preview)
        unidades_valid = unidades_valid and self._validate_detalhado_requires_units(form, unidades_formsets_preview)

        if not (form_valid and formset_valid and unidades_valid):
            context = self.get_context_data(form=form)
            context = self._inject_formsets_into_context(
                context, formset=formset, unidades_formsets=unidades_formsets_preview
            )
            return self.render_to_response(context)

        # Salva romaneio
        self.object = form.save(commit=False)
        self.object.usuario_cadastro = request.user
        self.object.save()

        # Salva itens
        formset.instance = self.object
        itens = formset.save()

        # Salva unidades e recalcula
        self._save_unidades_for_itens(request, itens)
        self._recalcular_totais_apos_salvar(self.object)

        messages.success(request, f"Romaneio {self.object.numero_romaneio} cadastrado com sucesso!")
        return redirect(self.get_success_url())


class RomaneioUpdateView(LoginRequiredMixin, _RomaneioFormsetsMixin, _RomaneioSaveMixin, UpdateView):
    model = Romaneio
    form_class = RomaneioForm
    template_name = "romaneio/romaneio_form.html"
    success_url = reverse_lazy("romaneio:romaneio_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return self._inject_formsets_into_context(context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()

        formset = ItemRomaneioFormSet(request.POST, instance=self.object)

        unidades_formsets = []
        for i, item_form in enumerate(formset.forms):
            prefix = f"unidades-{i}"
            instance = item_form.instance if getattr(item_form.instance, "pk", None) else None
            unidades_formsets.append(UnidadeRomaneioFormSet(request.POST, instance=instance, prefix=prefix))

        form_valid = form.is_valid()
        formset_valid = formset.is_valid()
        unidades_valid = all(uf.is_valid() for uf in unidades_formsets)

        if not (form_valid and formset_valid and unidades_valid):
            context = self.get_context_data(form=form)
            context = self._inject_formsets_into_context(context, formset=formset, unidades_formsets=unidades_formsets)
            return self.render_to_response(context)

        # Salva romaneio e itens
        self.object = form.save()
        formset.instance = self.object
        itens = formset.save()

        # Salva unidades e recalcula
        self._save_unidades_for_itens(request, itens)
        self._recalcular_totais_apos_salvar(self.object)

        messages.success(request, f"Romaneio {self.object.numero_romaneio} atualizado com sucesso!")
        return redirect(self.get_success_url())


class RomaneioDetailView(LoginRequiredMixin, DetailView):
    model = Romaneio
    template_name = "romaneio/romaneio_detail.html"
    context_object_name = "romaneio"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["itens"] = self.object.itens.select_related("tipo_madeira").prefetch_related("unidades")
        return context


@login_required
def get_preco_madeira(request):
    """
    Endpoint AJAX para buscar preço de madeira dinamicamente.
    """
    tipo_madeira_id = request.GET.get("tipo_madeira_id")
    tipo_romaneio = request.GET.get("tipo_romaneio")

    try:
        tipo_madeira = TipoMadeira.objects.get(id=tipo_madeira_id)
        preco = tipo_madeira.get_preco(tipo_romaneio)
        return JsonResponse({"success": True, "preco": float(preco)})
    except TipoMadeira.DoesNotExist:
        return JsonResponse({"success": False, "error": "Tipo de madeira não encontrado"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)