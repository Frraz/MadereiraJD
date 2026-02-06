from __future__ import annotations

from datetime import datetime

from django.contrib import messages
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


class RomaneioCreateView(LoginRequiredMixin, _RomaneioFormsetsMixin, CreateView):
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

        # DEBUG: Mostra o que está chegando no POST
        print("\n" + "=" * 80)
        print("🔍 DEBUG - POST DATA (unidades):")
        for key, value in request.POST.items():
            if 'unidades' in key:
                print(f"  {key}: {value}")
        print("=" * 80 + "\n")

        formset = ItemRomaneioFormSet(request.POST)

        # Constrói unidades_formsets SEM salvar itens ainda
        unidades_formsets_preview = []
        for i in range(len(formset.forms)):
            prefix = f"unidades-{i}"
            uf = UnidadeRomaneioFormSet(request.POST, instance=None, prefix=prefix)
            unidades_formsets_preview.append(uf)
            
            # DEBUG: Mostra se o formset de unidades é válido
            print(f"🔍 Unidades formset {i} (prefix={prefix}):")
            print(f"   - is_valid: {uf.is_valid()}")
            print(f"   - forms count: {len(uf.forms)}")
            if not uf.is_valid():
                print(f"   - errors: {uf.errors}")
                print(f"   - non_form_errors: {uf.non_form_errors()}")

        # Validação COMPLETA
        form_valid = form.is_valid()
        formset_valid = formset.is_valid()
        unidades_valid = all(uf.is_valid() for uf in unidades_formsets_preview)

        print(f"\n✅ Validação:")
        print(f"   - form_valid: {form_valid}")
        print(f"   - formset_valid: {formset_valid}")
        print(f"   - unidades_valid: {unidades_valid}")

        # VALIDAÇÃO MANUAL: se DETALHADO, cada item DEVE ter pelo menos 1 unidade
        if form_valid and form.cleaned_data.get('modalidade') == 'DETALHADO':
            print("\n🔍 Modalidade DETALHADO - validando unidades...")
            for i, uf in enumerate(unidades_formsets_preview):
                valid_units = sum(
                    1 for f in uf.forms 
                    if f.is_valid() and not f.cleaned_data.get('DELETE', False)
                )
                print(f"   - Item {i}: {valid_units} unidades válidas")
                
                if valid_units == 0:
                    print(f"   ❌ Item {i} não tem unidades!")
                    uf._non_form_errors.append("No modo DETALHADO, cada tipo de madeira deve ter pelo menos uma unidade.")
                    unidades_valid = False

        if not (form_valid and formset_valid and unidades_valid):
            print("\n❌ Validação falhou - renderizando form com erros\n")
            context = self.get_context_data(form=form)
            context = self._inject_formsets_into_context(
                context, formset=formset, unidades_formsets=unidades_formsets_preview
            )
            return self.render_to_response(context)

        print("\n✅ Todas validações OK - salvando...\n")

        # Tudo válido: salva romaneio
        self.object = form.save(commit=False)
        self.object.usuario_cadastro = request.user
        self.object.save()
        print(f"✅ Romaneio salvo: {self.object.pk}")

        # Salva itens
        formset.instance = self.object
        itens = formset.save()
        print(f"✅ {len(itens)} itens salvos")

        # Salva unidades
        for i, item in enumerate(itens):
            prefix = f"unidades-{i}"
            uf = UnidadeRomaneioFormSet(request.POST, instance=item, prefix=prefix)
            if uf.is_valid():
                unidades_salvas = uf.save()
                print(f"✅ Item {i}: {len(unidades_salvas)} unidades salvas")
            else:
                print(f"❌ Item {i}: erro ao salvar unidades - {uf.errors}")

        # Recalcula totais
        self.object.atualizar_totais()
        print(f"✅ Totais atualizados\n")

        messages.success(request, f"Romaneio {self.object.numero_romaneio} cadastrado com sucesso!")
        return redirect(self.get_success_url())


class RomaneioUpdateView(LoginRequiredMixin, _RomaneioFormsetsMixin, UpdateView):
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
            uf = UnidadeRomaneioFormSet(request.POST, instance=instance, prefix=prefix)
            unidades_formsets.append(uf)

        # Validação completa
        form_valid = form.is_valid()
        formset_valid = formset.is_valid()
        unidades_valid = all(uf.is_valid() for uf in unidades_formsets)

        if not (form_valid and formset_valid and unidades_valid):
            context = self.get_context_data(form=form)
            context = self._inject_formsets_into_context(
                context, formset=formset, unidades_formsets=unidades_formsets
            )
            return self.render_to_response(context)

        # Salva
        self.object = form.save()
        formset.instance = self.object
        itens = formset.save()

        for i, item in enumerate(itens):
            prefix = f"unidades-{i}"
            uf = UnidadeRomaneioFormSet(request.POST, instance=item, prefix=prefix)
            if uf.is_valid():
                uf.save()

        self.object.atualizar_totais()

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