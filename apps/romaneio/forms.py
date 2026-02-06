from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory

from apps.cadastros.models import Cliente, Motorista, TipoMadeira
from .models import ItemRomaneio, Romaneio, UnidadeRomaneio


# ================= ROMANEIO =================
class RomaneioForm(forms.ModelForm):
    """
    Form principal do Romaneio.
    - Filtra Cliente/Motorista apenas ativos
    - Widget HTML5 para data (YYYY-MM-DD)
    """

    class Meta:
        model = Romaneio
        fields = [
            "numero_romaneio",
            "data_romaneio",
            "cliente",
            "motorista",
            "tipo_romaneio",
            "modalidade",
        ]
        widgets = {
            "numero_romaneio": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: 11613"}),
            "data_romaneio": forms.DateInput(format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}),
            "cliente": forms.Select(attrs={"class": "form-control select2"}),
            "motorista": forms.Select(attrs={"class": "form-control select2"}),
            "tipo_romaneio": forms.Select(attrs={"class": "form-control"}),
            "modalidade": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["cliente"].queryset = Cliente.objects.filter(ativo=True).order_by("nome")
        self.fields["motorista"].queryset = Motorista.objects.filter(ativo=True).order_by("nome")
        self.fields["motorista"].required = False

        if self.instance and self.instance.pk and self.instance.data_romaneio:
            self.fields["data_romaneio"].initial = self.instance.data_romaneio.strftime("%Y-%m-%d")


# ================= ITEM ROMANEIO =================
class ItemRomaneioForm(forms.ModelForm):
    """
    Item do Romaneio:
    - Tipo de madeira
    - Quantidade total (m³)
      * SIMPLES: usuário informa
      * DETALHADO: calculado pelas unidades (campo pode vir preenchido pelo JS)
    - Valor unitário (m³)
    """

    class Meta:
        model = ItemRomaneio
        fields = [
            "tipo_madeira",
            "quantidade_m3_total",
            "valor_unitario",
        ]
        widgets = {
            "tipo_madeira": forms.Select(
                attrs={
                    "class": "form-control select2 tipo-madeira-select",
                    "onchange": "atualizarPrecoItem(this)",
                }
            ),
            "quantidade_m3_total": forms.NumberInput(
                attrs={
                    "class": "form-control quantidade-m3-total",
                    "step": "0.001",
                    "min": "0.001",
                    "placeholder": "0.000",
                    "inputmode": "decimal",
                }
            ),
            "valor_unitario": forms.NumberInput(
                attrs={
                    "class": "form-control valor-unitario",
                    "step": "0.01",
                    "min": "0.01",
                    "placeholder": "0.00",
                    "readonly": "readonly",
                    "inputmode": "decimal",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo_madeira"].queryset = TipoMadeira.objects.filter(ativo=True).order_by("nome")

    def clean_valor_unitario(self):
        valor = self.cleaned_data.get("valor_unitario")
        if valor is None or valor <= Decimal("0.00"):
            raise ValidationError("O valor unitário deve ser maior que zero!")
        return valor

    def clean_quantidade_m3_total(self):
        """
        Aceita qualquer valor >= 0 (inclusive 0 no DETALHADO durante submit).
        O model/view vão recalcular após salvar unidades.
        """
        qtd = self.cleaned_data.get("quantidade_m3_total")
        if qtd is None:
            qtd = Decimal("0.000")

        if qtd < Decimal("0.000"):
            raise ValidationError("A quantidade não pode ser negativa.")

        return qtd


class BaseItemRomaneioFormSet(BaseInlineFormSet):
    """
    - Exige pelo menos 1 item não deletado
    - Valida duplicidade de tipo_madeira por romaneio
    """

    def clean(self):
        super().clean()

        if any(self.errors):
            return

        valid_forms = [
            f for f in self.forms
            if getattr(f, "cleaned_data", None) and not f.cleaned_data.get("DELETE")
        ]

        if len(valid_forms) < 1:
            raise ValidationError("O romaneio precisa ter pelo menos um item (tipo de madeira).")

        # Valida duplicidade de tipo_madeira
        tipos = []
        for f in valid_forms:
            tm = f.cleaned_data.get("tipo_madeira")
            if tm:
                if tm.pk in tipos:
                    raise ValidationError(f"O tipo de madeira '{tm.nome}' está duplicado neste romaneio.")
                tipos.append(tm.pk)


ItemRomaneioFormSet = inlineformset_factory(
    parent_model=Romaneio,
    model=ItemRomaneio,
    form=ItemRomaneioForm,
    formset=BaseItemRomaneioFormSet,
    extra=0,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


# ================= UNIDADE ROMANEIO =================
class UnidadeRomaneioForm(forms.ModelForm):
    """
    Unidade (tora) do item.
    - Comprimento, rôdo, descontos
    - Quantidade m³ é calculada automaticamente pelo JS (e validada no backend)
    """

    class Meta:
        model = UnidadeRomaneio
        fields = [
            "comprimento",
            "rodo",
            "desconto_1",
            "desconto_2",
            "quantidade_m3",
        ]
        widgets = {
            "comprimento": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-sm campo-detalhado campo-unidade",
                    "step": "0.01",
                    "min": "0.01",
                    "placeholder": "Ex: 3.00",
                    "inputmode": "decimal",
                }
            ),
            "rodo": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-sm campo-detalhado campo-unidade",
                    "step": "0.01",
                    "min": "0.01",
                    "placeholder": "Ex: 40.00",
                    "inputmode": "decimal",
                }
            ),
            "desconto_1": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-sm campo-detalhado campo-unidade",
                    "step": "0.01",
                    "min": "0.00",
                    "placeholder": "0.00",
                    "inputmode": "decimal",
                }
            ),
            "desconto_2": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-sm campo-detalhado campo-unidade",
                    "step": "0.01",
                    "min": "0.00",
                    "placeholder": "0.00",
                    "inputmode": "decimal",
                }
            ),
            "quantidade_m3": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-sm campo-unidade quantidade-m3",
                    "step": "0.001",
                    "min": "0.001",
                    "placeholder": "0.000",
                    "inputmode": "decimal",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Define valores padrão para descontos em unidades novas
        if not (self.instance and self.instance.pk):
            self.fields["desconto_1"].initial = Decimal("0.00")
            self.fields["desconto_2"].initial = Decimal("0.00")

    def clean(self):
        cleaned_data = super().clean()

        # Normaliza descontos vazios para 0.00
        for field in ("desconto_1", "desconto_2"):
            if cleaned_data.get(field) is None:
                cleaned_data[field] = Decimal("0.00")

        # Valida se comprimento e rôdo foram preenchidos
        comprimento = cleaned_data.get("comprimento")
        rodo = cleaned_data.get("rodo")

        if comprimento and comprimento <= Decimal("0.00"):
            self.add_error("comprimento", "O comprimento deve ser maior que zero.")

        if rodo and rodo <= Decimal("0.00"):
            self.add_error("rodo", "O rôdo deve ser maior que zero.")

        return cleaned_data

    def clean_quantidade_m3(self):
        qtd = self.cleaned_data.get("quantidade_m3")
        
        # Se a unidade está sendo deletada, não precisa validar
        if self.cleaned_data.get("DELETE"):
            return qtd

        if qtd is None or qtd <= Decimal("0.000"):
            raise ValidationError("A quantidade (m³) deve ser maior que zero.")
        
        return qtd


class BaseUnidadeRomaneioFormSet(BaseInlineFormSet):
    """
    Formset de unidades (toras) de um item.
    - NO MÍNIMO 0 unidades durante validação inicial (para permitir POST incremental)
    - Validação manual na view garante que DETALHADO tenha pelo menos 1 unidade válida
    """

    def clean(self):
        super().clean()

        if any(self.errors):
            return

        # Conta unidades válidas (não deletadas)
        valid_forms = [
            f for f in self.forms
            if f.is_valid() and 
            getattr(f, "cleaned_data", None) and 
            not f.cleaned_data.get("DELETE")
        ]

        # Se não há unidades válidas, não faz mais validações (a view vai lidar com isso)
        if len(valid_forms) == 0:
            return

        # Valida que cada unidade válida tem comprimento e rôdo
        for form in valid_forms:
            comprimento = form.cleaned_data.get("comprimento")
            rodo = form.cleaned_data.get("rodo")

            if not comprimento or comprimento <= Decimal("0.00"):
                form.add_error("comprimento", "Comprimento é obrigatório.")
            
            if not rodo or rodo <= Decimal("0.00"):
                form.add_error("rodo", "Rôdo é obrigatório.")


UnidadeRomaneioFormSet = inlineformset_factory(
    parent_model=ItemRomaneio,
    model=UnidadeRomaneio,
    form=UnidadeRomaneioForm,
    formset=BaseUnidadeRomaneioFormSet,
    extra=0,
    can_delete=True,
    min_num=0,  # ← CORRIGIDO: permite 0 durante validação inicial
    validate_min=False,  # ← Validação manual na view
)