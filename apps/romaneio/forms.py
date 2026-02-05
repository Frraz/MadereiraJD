from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory

from apps.cadastros.models import Cliente, Motorista, TipoMadeira
from .models import Romaneio, ItemRomaneio


# ================= ROMANEIO (ÚNICO) =================
class RomaneioForm(forms.ModelForm):
    class Meta:
        model = Romaneio
        fields = [
            "numero_romaneio",
            "data_romaneio",
            "cliente",
            "motorista",
            "tipo_romaneio",
            "modalidade",
            "desconto",
        ]
        widgets = {
            "numero_romaneio": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: 11613"}),
            "data_romaneio": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "cliente": forms.Select(attrs={"class": "form-control select2"}),
            "motorista": forms.Select(attrs={"class": "form-control select2"}),
            "tipo_romaneio": forms.Select(attrs={"class": "form-control"}),
            "modalidade": forms.Select(attrs={"class": "form-control"}),
            "desconto": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "0.00",
                "step": "0.01",
                "min": 0,
                "max": 100,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cliente"].queryset = Cliente.objects.filter(ativo=True)
        self.fields["motorista"].queryset = Motorista.objects.filter(ativo=True)

        # Opcional: ao criar, já deixa SIMPLES por padrão (model já tem default)
        # self.fields["modalidade"].initial = "SIMPLES"

    def clean_desconto(self):
        desconto = self.cleaned_data.get("desconto")
        if desconto is None:
            return Decimal("0.00")
        if desconto < 0 or desconto > 100:
            raise ValidationError("O desconto deve estar entre 0 e 100.")
        return desconto


class ItemRomaneioForm(forms.ModelForm):
    class Meta:
        model = ItemRomaneio
        fields = [
            "tipo_madeira",
            "comprimento",
            "rodo",
            "quantidade_m3",
            "valor_unitario",
        ]
        widgets = {
            "tipo_madeira": forms.Select(attrs={
                "class": "form-control select2 tipo-madeira-select",
                "onchange": "atualizarPreco(this)",
            }),
            # Campos "detalhados" (serão obrigatórios via formset quando modalidade=DETALHADO)
            "comprimento": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0.01",
                "placeholder": "Ex: 3.00",
            }),
            "rodo": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Rôdo",
            }),
            "quantidade_m3": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.001",
                "min": "0.001",
                "placeholder": "0.000",
                "onchange": "calcularTotal(this)",
            }),
            "valor_unitario": forms.NumberInput(attrs={
                "class": "form-control valor-unitario",
                "step": "0.01",
                "min": "0.01",
                "placeholder": "0.00",
                "readonly": "readonly",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo_madeira"].queryset = TipoMadeira.objects.filter(ativo=True)

    def clean_quantidade_m3(self):
        qtd = self.cleaned_data.get("quantidade_m3")
        if qtd is None or qtd <= Decimal("0.000"):
            raise ValidationError("A quantidade deve ser maior que zero!")
        return qtd

    def clean_valor_unitario(self):
        valor = self.cleaned_data.get("valor_unitario")
        if valor is None or valor <= Decimal("0.00"):
            raise ValidationError("O valor unitário deve ser maior que zero!")
        return valor


class BaseItemRomaneioFormSet(BaseInlineFormSet):
    """
    Valida itens conforme modalidade do romaneio:
    - SIMPLES: comprimento/rodo podem ficar vazios
    - DETALHADO: comprimento obrigatório (>0) e rodo obrigatório
    """

    def clean(self):
        super().clean()

        # Se algum form já tem erro individual, não duplica erros aqui
        if any(self.errors):
            return

        modalidade = None
        if self.instance and getattr(self.instance, "modalidade", None):
            modalidade = self.instance.modalidade

        # Em Create, instance ainda não tem modalidade salva.
        # Então tentamos ler do POST via prefixo do formulário pai.
        # (Se não achar, não bloqueia; o ideal é passar a modalidade via view para o formset se quiser 100% garantido.)
        if modalidade is None and self.data:
            # o RomaneioForm costuma ter prefix vazio, então o campo vira "modalidade"
            modalidade = self.data.get("modalidade") or self.data.get("romaneio-modalidade")

        if modalidade != "DETALHADO":
            return

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue

            comprimento = form.cleaned_data.get("comprimento")
            rodo = (form.cleaned_data.get("rodo") or "").strip()

            if comprimento is None or comprimento <= Decimal("0.00"):
                form.add_error("comprimento", "Comprimento é obrigatório na modalidade Detalhado.")
            if not rodo:
                form.add_error("rodo", "Rôdo é obrigatório na modalidade Detalhado.")


ItemRomaneioFormSet = inlineformset_factory(
    parent_model=Romaneio,
    model=ItemRomaneio,
    form=ItemRomaneioForm,
    formset=BaseItemRomaneioFormSet,
    extra=0,          # <- sempre 1 linha ao criar
    can_delete=True,
    min_num=1,
    validate_min=True,
)