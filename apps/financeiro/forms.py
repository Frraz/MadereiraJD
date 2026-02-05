from django import forms
from .models import Pagamento
from apps.cadastros.models import Cliente
from decimal import Decimal

class PagamentoForm(forms.ModelForm):
    class Meta:
        model = Pagamento
        fields = ['data_pagamento', 'cliente', 'valor', 'tipo_pagamento', 'descricao']
        widgets = {
            'data_pagamento': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                }
            ),
            'cliente': forms.Select(attrs={
                'class': 'form-control select2',
            }),
            'valor': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0,00'
            }),
            'tipo_pagamento': forms.Select(attrs={
                'class': 'form-control'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ex: PIX C/C TROPICAL AGRO, PAGAMENTO EM ESPÉCIE'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].queryset = Cliente.objects.filter(ativo=True)
        # Garante que a data apareça ao editar, no formato exigido pelo input date
        if self.instance and self.instance.pk and self.instance.data_pagamento:
            self.fields['data_pagamento'].initial = self.instance.data_pagamento.strftime('%Y-%m-%d')

    def clean_valor(self):
        valor = self.cleaned_data.get('valor')
        if valor is None or valor <= Decimal('0.00'):
            raise forms.ValidationError('Informe um valor de pagamento válido (maior que zero).')
        return valor