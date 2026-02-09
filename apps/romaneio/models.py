from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum

from apps.cadastros.models import Cliente, Motorista, TipoMadeira

QTD_M3_STEP = Decimal("0.001")
VALOR_STEP = Decimal("0.01")


class Romaneio(models.Model):
    """Romaneio único (Simples/Detalhado)."""

    TIPO_ROMANEIO_CHOICES = [
        ("NORMAL", "Normal"),
        ("COM_FRETE", "Com Frete"),
    ]

    MODALIDADE_CHOICES = [
        ("SIMPLES", "Simples"),
        ("DETALHADO", "Detalhado"),
    ]

    numero_romaneio = models.CharField(max_length=20, unique=True, db_index=True)
    data_romaneio = models.DateField(db_index=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="romaneios")
    motorista = models.ForeignKey(
        Motorista,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="romaneios",
    )

    tipo_romaneio = models.CharField(max_length=15, choices=TIPO_ROMANEIO_CHOICES, default="NORMAL")
    modalidade = models.CharField(max_length=10, choices=MODALIDADE_CHOICES, default="SIMPLES")

    m3_total = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal("0.000"), editable=False)
    valor_bruto = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"), editable=False)
    valor_total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"), editable=False)

    usuario_cadastro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="romaneios_cadastrados",
    )
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data_romaneio", "-numero_romaneio"]
        verbose_name = "Romaneio"
        verbose_name_plural = "Romaneios"

    def __str__(self) -> str:
        return (
            f"Romaneio {self.numero_romaneio} ({self.get_modalidade_display()})"
            f" - {self.cliente.nome} - {self.data_romaneio:%d/%m/%Y}"
        )

    def atualizar_totais(self, *, save: bool = True) -> None:
        """
        Atualiza valor_bruto, valor_total (líquido) e m3_total com base nos itens.

        - valor_bruto: soma dos itens sem desconto
        - valor_total: valor final com desconto do romaneio (percentual)
        """
        totais = self.itens.aggregate(
            total_valor=Sum("valor_total"),
            total_m3=Sum("quantidade_m3_total"),
        )

        bruto = (totais["total_valor"] or Decimal("0.00")).quantize(VALOR_STEP, rounding=ROUND_HALF_UP)
        m3 = (totais["total_m3"] or Decimal("0.000")).quantize(QTD_M3_STEP, rounding=ROUND_HALF_UP)

        desconto_pct = getattr(self, "desconto", None) or Decimal("0.00")  # em %
        # garante faixa [0, 100]
        if desconto_pct < 0:
            desconto_pct = Decimal("0.00")
        if desconto_pct > 100:
            desconto_pct = Decimal("100.00")

        fator = (Decimal("100.00") - desconto_pct) / Decimal("100.00")
        liquido = (bruto * fator).quantize(VALOR_STEP, rounding=ROUND_HALF_UP)

        self.valor_bruto = bruto
        self.valor_total = liquido
        self.m3_total = m3

        if save:
            update_fields = ["valor_bruto", "valor_total", "m3_total"]
            super().save(update_fields=update_fields)


class ItemRomaneio(models.Model):
    """
    Item do romaneio - representa um TIPO DE MADEIRA.
    - SIMPLES: usuário informa quantidade_m3_total diretamente.
    - DETALHADO: quantidade_m3_total vem da soma das unidades.
    """

    romaneio = models.ForeignKey(Romaneio, on_delete=models.CASCADE, related_name="itens")
    tipo_madeira = models.ForeignKey(TipoMadeira, on_delete=models.PROTECT, related_name="itens_romaneio")

    valor_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Valor/m³",
    )

    quantidade_m3_total = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=Decimal("0.000"),
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name="Total m³",
    )

    valor_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
    )

    class Meta:
        ordering = ["romaneio", "tipo_madeira", "id"]
        verbose_name = "Item do Romaneio"
        verbose_name_plural = "Itens do Romaneio"

    def __str__(self) -> str:
        nome = self.tipo_madeira.nome if self.tipo_madeira else ""
        qtd_unidades = self.unidades.count()
        return f"{nome} - {qtd_unidades} unidade(s) - {self.quantidade_m3_total:.3f} m³"

    def _get_modalidade_romaneio(self) -> str | None:
        """
        Retorna a modalidade do romaneio de forma robusta.

        Em alguns fluxos (ex.: create via formset.save), self.romaneio pode não estar
        carregado no objeto em memória; mas o romaneio_id existe. Então consultamos
        o banco apenas se necessário.
        """
        if not self.romaneio_id:
            return None

        if getattr(self, "romaneio", None) is not None:
            return self.romaneio.modalidade

        return Romaneio.objects.only("modalidade").get(pk=self.romaneio_id).modalidade

    def atualizar_totais(self, *, save: bool = True, atualizar_romaneio: bool = True) -> None:
        """
        Atualiza os totais deste item.
        - DETALHADO: soma unidades e sobrescreve quantidade_m3_total
        - SIMPLES: usa quantidade_m3_total informada
        """
        modalidade = self._get_modalidade_romaneio()

        if modalidade == "DETALHADO":
            totais = self.unidades.aggregate(total_m3=Sum("quantidade_m3"))
            m3 = (totais["total_m3"] or Decimal("0.000")).quantize(QTD_M3_STEP, rounding=ROUND_HALF_UP)
            self.quantidade_m3_total = m3
        else:
            self.quantidade_m3_total = (self.quantidade_m3_total or Decimal("0.000")).quantize(
                QTD_M3_STEP, rounding=ROUND_HALF_UP
            )

        self.valor_total = (self.quantidade_m3_total * (self.valor_unitario or Decimal("0.00"))).quantize(
            VALOR_STEP, rounding=ROUND_HALF_UP
        )

        if save:
            super().save(update_fields=["quantidade_m3_total", "valor_total"])

        if atualizar_romaneio and self.romaneio_id:
            self.romaneio.atualizar_totais()

    def save(self, *args, **kwargs):
        # Preço automático se possível e se valor_unitario estiver vazio/zerado
        if (self.valor_unitario in (None, Decimal("0.00"))) and self.romaneio_id and self.tipo_madeira_id:
            self.valor_unitario = self.tipo_madeira.get_preco(self.romaneio.tipo_romaneio)

        # No SIMPLES, garantimos coerência do valor_total antes de salvar.
        if self.romaneio_id and self.romaneio.modalidade == "SIMPLES":
            self.quantidade_m3_total = (self.quantidade_m3_total or Decimal("0.000")).quantize(
                QTD_M3_STEP, rounding=ROUND_HALF_UP
            )
            self.valor_total = (self.quantidade_m3_total * (self.valor_unitario or Decimal("0.00"))).quantize(
                VALOR_STEP, rounding=ROUND_HALF_UP
            )

        super().save(*args, **kwargs)

        # Pós-save:
        # - SIMPLES: atualiza romaneio imediatamente
        # - DETALHADO: quem recalcula é UnidadeRomaneio.save/delete (e/ou a view ao final)
        if self.romaneio_id and self.romaneio.modalidade == "SIMPLES":
            self.romaneio.atualizar_totais()

    def delete(self, *args, **kwargs):
        rom = self.romaneio
        super().delete(*args, **kwargs)
        if rom:
            rom.atualizar_totais()


class UnidadeRomaneio(models.Model):
    item = models.ForeignKey(ItemRomaneio, on_delete=models.CASCADE, related_name="unidades")

    comprimento = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True, verbose_name="Comprimento (m)"
    )
    rodo = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True, verbose_name="Rôdo (cm)"
    )
    desconto_1 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, default=Decimal("0.00"))
    desconto_2 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, default=Decimal("0.00"))

    quantidade_m3 = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name="Quantidade (m³)",
    )

    class Meta:
        ordering = ["item", "id"]
        verbose_name = "Unidade do Romaneio"
        verbose_name_plural = "Unidades do Romaneio"

    def __str__(self) -> str:
        return f"Unidade #{self.id} - {self.quantidade_m3:.3f} m³"

    def calcular_m3_detalhado(self) -> Decimal | None:
        if self.rodo is None or self.comprimento is None:
            return None

        desc1 = self.desconto_1 or Decimal("0.00")
        desc2 = self.desconto_2 or Decimal("0.00")

        parte_rodo = ((self.rodo / Decimal("4")) ** 2 * self.comprimento) / Decimal("1000000")
        parte_desconto = (desc1 * desc2 * self.comprimento) / Decimal("1000000")
        m3_liquida = parte_rodo - parte_desconto

        return m3_liquida.quantize(QTD_M3_STEP, rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        # No DETALHADO, só recalcula pela fórmula se quantidade_m3 estiver vazia/zerada.
        if self.item_id and self.item._get_modalidade_romaneio() == "DETALHADO":
            qtd_atual = self.quantidade_m3
            if qtd_atual is None or qtd_atual <= Decimal("0.000"):
                m3_calc = self.calcular_m3_detalhado()
                if m3_calc is not None:
                    self.quantidade_m3 = m3_calc

        super().save(*args, **kwargs)

        if self.item_id:
            self.item.atualizar_totais(save=True, atualizar_romaneio=True)

    def delete(self, *args, **kwargs):
        item = self.item
        super().delete(*args, **kwargs)
        if item:
            item.atualizar_totais(save=True, atualizar_romaneio=True)