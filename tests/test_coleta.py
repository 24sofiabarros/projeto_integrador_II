"""
==============================================================================
Testes Automatizados para a Tarefa E1 - Sprint 3 (SITRIB)
Validação de:
  1. Autenticação Bearer Token (200, 401, 403)
  2. Paginação Automática
  3. Rate-Limiting e atraso de requisições (>= 1.0s)
  4. Anonimização LGPD e expurgo de dados sensíveis
  5. Persistência de dados brutos datados em data/bruto/
==============================================================================
"""

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from src.coleta.coleta_api import (
    AcessoNegadoError,
    AutenticacaoInvalidaError,
    ColetorAPISefin,
    ServidorSimuladorSefin,
    anonimizar_cnpj,
    anonimizar_cpf,
    anonimizar_registro_lgpd,
)


class TestAnonimizacaoLGPD(unittest.TestCase):
    """Testes unitários para conformidade LGPD."""

    def test_anonimizacao_cpf_formatado(self):
        cpf = "111.222.333-00"
        cpf_anonimizado = anonimizar_cpf(cpf)
        self.assertEqual(cpf_anonimizado, "***.***.333-**")

    def test_anonimizacao_cpf_apenas_digitos(self):
        cpf = "12345678900"
        cpf_anonimizado = anonimizar_cpf(cpf)
        self.assertEqual(cpf_anonimizado, "***.***.789-**")

    def test_anonimizacao_cnpj_formatado(self):
        cnpj = "33.444.555/0001-66"
        cnpj_anonimizado = anonimizar_cnpj(cnpj)
        self.assertEqual(cnpj_anonimizado, "33.444.555/****-**")

    def test_anonimizacao_cnpj_apenas_digitos(self):
        cnpj = "12345678000199"
        cnpj_anonimizado = anonimizar_cnpj(cnpj)
        self.assertEqual(cnpj_anonimizado, "12.345.678/****-**")

    def test_expurgo_dados_sensiveis(self):
        registro = {
            "id": 1,
            "nome": "João Silva",
            "cpf": "111.222.333-00",
            "telefone": "(63) 99123-4567",
            "telefone_fixo": "(63) 3215-0000",
            "telefone_devedor": "(63) 98888-7777",
            "celular_contato": "(63) 99999-1111",
            "email": "joao@emailpessoal.com",
            "email_pessoal": "particular@email.com",
            "email_devedor": "devedor@email.com",
            "valor_devido": 1500.0,
        }

        limpo = anonimizar_registro_lgpd(registro)

        # Campos que DEVEM ser anonimizados
        self.assertEqual(limpo["cpf"], "***.***.333-**")
        self.assertEqual(limpo["nome"], "João Silva")
        self.assertEqual(limpo["valor_devido"], 1500.0)

        # Campos que DEVEM ser totalmente removidos (expurgados)
        self.assertNotIn("telefone", limpo)
        self.assertNotIn("telefone_fixo", limpo)
        self.assertNotIn("telefone_devedor", limpo)
        self.assertNotIn("celular_contato", limpo)
        self.assertNotIn("email", limpo)
        self.assertNotIn("email_pessoal", limpo)
        self.assertNotIn("email_devedor", limpo)


class TestColetorAPISefinComMock(unittest.TestCase):
    """Testes de integração com o servidor REST simulador."""

    @classmethod
    def setUpClass(cls):
        cls.porta = 8899
        cls.servidor = ServidorSimuladorSefin(host="127.0.0.1", porta=cls.porta)
        cls.servidor.iniciar()
        cls.base_url = f"http://127.0.0.1:{cls.porta}"
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.servidor.parar()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_autenticacao_sucesso(self):
        coletor = ColetorAPISefin(
            base_url=self.base_url,
            token="token_valido_teste",
            rate_limit_delay=1.0,
        )
        dados = coletor.coletar_paginado("arrecadacao/iptu")
        self.assertGreater(len(dados), 0)

    def test_autenticacao_invalida_401(self):
        coletor = ColetorAPISefin(
            base_url=self.base_url,
            token="token_invalido",
            rate_limit_delay=1.0,
        )
        with self.assertRaises(AutenticacaoInvalidaError):
            coletor.coletar_paginado("arrecadacao/iptu")

    def test_acesso_negado_403(self):
        coletor = ColetorAPISefin(
            base_url=self.base_url,
            token="token_sem_permissao",
            rate_limit_delay=1.0,
        )
        with self.assertRaises(AcessoNegadoError):
            coletor.coletar_paginado("arrecadacao/iptu")

    def test_paginacao_automatica(self):
        coletor = ColetorAPISefin(
            base_url=self.base_url,
            token="token_valido_teste",
            rate_limit_delay=1.0,
        )
        # O mock possui 3 registros divididos em páginas de 2
        dados = coletor.coletar_paginado("arrecadacao/iptu")
        self.assertEqual(len(dados), 3)

    def test_rate_limiting_delay(self):
        coletor = ColetorAPISefin(
            base_url=self.base_url,
            token="token_valido_teste",
            rate_limit_delay=1.0,
        )
        t_inicio = time.time()
        # Coleta IPTU que fará 2 requisições (página 1 e página 2)
        coletor.coletar_paginado("arrecadacao/iptu")
        duracao = time.time() - t_inicio
        # Deve ter demorado pelo menos 1.0s entre as chamadas
        self.assertGreaterEqual(duracao, 1.0)

    def test_persistencia_com_timestamp_e_lgpd(self):
        coletor = ColetorAPISefin(
            base_url=self.base_url,
            token="token_valido_teste",
            rate_limit_delay=1.0,
        )
        dados = coletor.coletar_paginado("arrecadacao/iptu")
        arquivo = coletor.persistir_dados(dados, "iptu", diretorio_destino=self.temp_dir)

        self.assertTrue(arquivo.exists())
        self.assertTrue(arquivo.name.startswith("iptu_"))
        self.assertTrue(arquivo.name.endswith(".json"))

        with open(arquivo, "r", encoding="utf-8") as f:
            conteudo = json.load(f)

        self.assertEqual(conteudo["categoria"], "iptu")
        self.assertEqual(conteudo["total_registros"], len(dados))
        self.assertIn("timestamp_coleta", conteudo)

        # Verifica anonimização no arquivo gravado
        for reg in conteudo["dados"]:
            self.assertTrue(reg["cpf_contribuinte"].startswith("***.***."))
            self.assertTrue(reg["cpf_contribuinte"].endswith("-**"))
            self.assertNotIn("telefone", reg)
            self.assertNotIn("email", reg)


if __name__ == "__main__":
    unittest.main()
