from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.cadastros.models import TipoMadeira, Motorista, Cliente
from apps.romaneio.models import Romaneio
from apps.financeiro.models import Pagamento
from decimal import Decimal
from django.db import models
import random
from datetime import date, timedelta

class Command(BaseCommand):
    help = "Cria 60 tipos de madeira, 60 usuários, 60 motoristas, 60 clientes, 200 romaneios e 200 pagamentos para testes."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("==== Mock Massivo de Dados para Teste ===="))

        # 1. Tipos de Madeira
        self.stdout.write("Criando tipos de madeira...")
        for i in range(1, 61):
            TipoMadeira.objects.get_or_create(
                nome=f"Madeira Teste {i}",
                defaults={
                    "preco_normal": Decimal(f"{random.uniform(100,300):.2f}"),
                    "preco_com_frete": Decimal(f"{random.uniform(150,350):.2f}"),
                    "ativo": True,
                }
            )

        # 2. Clientes
        self.stdout.write("Criando clientes...")
        for i in range(1, 61):
            Cliente.objects.get_or_create(
                nome=f"Cliente Teste {i}",
                defaults={
                    "cpf_cnpj": f"000.000.000-00",
                    "telefone": f"99999-{i:04d}",
                    "ativo": True,
                }
            )

        # 3. Motoristas
        self.stdout.write("Criando motoristas...")
        for i in range(1, 61):
            Motorista.objects.get_or_create(
                nome=f"Motorista Teste {i}",
                defaults={
                    "cpf": f"000.000.000-00",
                    "placa_veiculo": f"ABC{i:04d}",
                    "telefone": f"98888-{i:04d}",
                    "ativo": True,
                }
            )

        # 4. Usuários
        self.stdout.write("Criando usuários...")
        for i in range(1, 61):
            User.objects.get_or_create(
                username=f"user_teste{i}",
                defaults={
                    "first_name": f"Usuário {i}",
                    "email": f"user{i}@teste.com",
                    "is_staff": True,
                    "is_active": True,
                }
            )

        # 5. Romaneios
        self.stdout.write("Criando 200 romaneios...")
        tipos = list(TipoMadeira.objects.all())
        motoristas = list(Motorista.objects.all())
        clientes = list(Cliente.objects.all())
        data_base = date.today() - timedelta(days=200)
        # Descobre próximo número de romaneio disponível (inteiro mais alto + 1)
        try:
            maior_existente = max([
                int(r.numero_romaneio)
                for r in Romaneio.objects.all()
                if str(r.numero_romaneio).isdigit()
            ], default=10000)
        except Exception:
            maior_existente = 10000
        start = maior_existente + 1
        for i in range(0, 200):
            cliente = random.choice(clientes)
            motorista = random.choice(motoristas)
            tipo = random.choice(tipos)
            n_romaneio = str(start + i)
            data_romaneio = data_base + timedelta(days=random.randint(0, 200))
            desconto = Decimal(f"{random.uniform(0,30):.2f}")
            modalidade = random.choice(["SIMPLES", "DETALHADO"])
            tipo_romaneio = random.choice(["NORMAL", "COM_FRETE"])

            romaneio, created = Romaneio.objects.get_or_create(
                numero_romaneio=n_romaneio,
                defaults={
                    "cliente": cliente,
                    "motorista": motorista,
                    "tipo_romaneio": tipo_romaneio,
                    "modalidade": modalidade,
                    "data_romaneio": data_romaneio,
                    "desconto": desconto,
                    # valores default, sobrescritos normalmente por itens
                    "m3_total": Decimal(f"{random.uniform(2, 100):.3f}"),
                    "valor_bruto": Decimal(f"{random.uniform(500, 10000):.2f}"),
                    "valor_total": Decimal(f"{random.uniform(500, 10000):.2f}"),
                }
            )
            # Opcional: pode criar 1-3 ItensRomaneio para cada romaneio aqui!

        # 6. Pagamentos
        self.stdout.write("Criando 200 pagamentos...")
        for i in range(0, 200):
            cliente = random.choice(clientes)
            data_pagamento = data_base + timedelta(days=random.randint(0, 200))
            Pagamento.objects.create(
                cliente=cliente,
                data_pagamento=data_pagamento,
                valor=Decimal(f"{random.uniform(350, 15000):.2f}"),
                tipo_pagamento=random.choice(['DINHEIRO', 'PIX', 'TRANSFERENCIA', 'CHEQUE', 'DEPOSITO', 'OUTROS']),
                descricao=f"Pagamento teste {i+1}"
            )
        self.stdout.write(self.style.SUCCESS("Mock concluído com sucesso!"))