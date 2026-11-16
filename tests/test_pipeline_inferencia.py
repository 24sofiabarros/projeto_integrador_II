"""
========================================================================================
Testes Automatizados para o Pipeline de Carregamento e Inferência (Sprint 4 - SITRIB)
Integrante: Hyag Herrcolis Silva Queiroz
Validação de:
  1. Gerenciamento e cache de artefatos serializados (.joblib).
  2. Tratamento de exceções (ModeloNaoEncontradoError, DadosIncompativeisError).
  3. Integridade dos modelos (SHA-256).
  4. Saneamento e validação defensiva de features de entrada.
  5. Inferência probabilística com Random Forest e XGBoost.
  6. Integração completa com o Motor de Scoring de Recuperabilidade.
  7. Priorização com FilaCobrancaHeap (Heap Máximo com exclusão de IPTU Social).
========================================================================================
"""

import os
import unittest
import pandas as pd
import numpy as np

from src.pipeline.carregamento_inferencia import (
    GerenciadorModelos,
    PipelineInferencia,
    ModeloNaoEncontradoError,
    DadosIncompativeisError,
    get_pipeline_inferencia_singleton,
)
from src.scoring.recuperabilidade import FaixaRecuperabilidade


class TestGerenciadorModelos(unittest.TestCase):
    """Testes unitários para o carregador de modelos e verificação de artefatos."""

    def setUp(self):
        self.gerenciador = GerenciadorModelos()

    def test_listar_modelos_disponiveis(self):
        lista = self.gerenciador.listar_modelos_disponiveis()
        self.assertGreaterEqual(len(lista), 3)
        nomes = [m["nome_arquivo"] for m in lista]
        self.assertIn("random_forest_debt_model.joblib", nomes)
        self.assertIn("logistic_regression_baseline.joblib", nomes)
        self.assertIn("decision_tree_baseline.joblib", nomes)

        # Checa presença de campos de integridade
        item_rf = next(m for m in lista if m["nome_arquivo"] == "random_forest_debt_model.joblib")
        self.assertTrue(item_rf["is_campeao"])
        self.assertGreater(item_rf["tamanho_kb"], 0)
        self.assertTrue(len(item_rf["hash_sha256"]) >= 8)

    def test_carregamento_com_cache(self):
        # Primeira chamada carrega do disco
        m1 = self.gerenciador.carregar_modelo("random_forest_debt_model.joblib")
        self.assertTrue(hasattr(m1, "predict"))

        # Segunda chamada deve recuperar a mesma instância do cache
        m2 = self.gerenciador.carregar_modelo("random_forest_debt_model.joblib")
        self.assertIs(m1, m2)

    def test_modelo_inexistente_levanta_excecao(self):
        with self.assertRaises(ModeloNaoEncontradoError):
            self.gerenciador.carregar_modelo("modelo_fantasma_xyz.joblib")

    def test_carregar_metricas_auditoria(self):
        metricas = self.gerenciador.carregar_metricas_auditoria()
        self.assertIsNotNone(metricas)
        self.assertIn("Random Forest (Modelo Final Campeão)", metricas)


class TestPipelineInferencia(unittest.TestCase):
    """Testes de ponta a ponta para o pipeline de inferência preditiva."""

    def setUp(self):
        self.pipeline = PipelineInferencia()

    def test_validacao_dataframe_vazio_levanta_erro(self):
        with self.assertRaises(DadosIncompativeisError):
            self.pipeline.validar_e_sanear_dados(pd.DataFrame())

    def test_saneamento_features_ausentes(self):
        """Um DataFrame incompleto deve ter features imputadas sem quebrar o pipeline."""
        df_incompleto = pd.DataFrame({
            "valor_principal": [3500.0, 12000.0],
            "tributo": ["IPTU", "ISSQN"],
            # Colunas ausentes propositalmente: tempo_inscricao_meses, regiao, etc.
        })
        df_san = self.pipeline.validar_e_sanear_dados(df_incompleto)
        for col in self.pipeline.TODAS_FEATURES:
            self.assertIn(col, df_san.columns)
        self.assertIn("valor_total_divida", df_san.columns)

    def test_execucao_inferencia_ponta_a_ponta_rf(self):
        """Executa inferência completa com o modelo campeão Random Forest."""
        df_teste = pd.DataFrame({
            "id_devedor": ["DIV-101", "DIV-102"],
            "tributo": ["IPTU", "ISSQN"],
            "tipo_pessoa": ["Pessoa Física (PF)", "Pessoa Jurídica (PJ)"],
            "tempo_inscricao_meses": [12, 60],
            "valor_principal": [2000.0, 85000.0],
            "juros_multas": [200.0, 15000.0],
            "valor_total_divida": [2200.0, 100000.0],
            "quantidade_debitos": [1, 5],
            "historico_parcelamentos": [1, 0],
            "execucao_ajuizada": ["Não", "Sim"],
            "possui_bens": ["Sim", "Não"],
            "contato_atualizado": ["Sim", "Não"],
            "faixa_renda": ["5 a 10 SM", "Até 2 SM"],
            "regiao": ["Plano Diretor Sul", "Região Sul (Taquaralto)"],
            "isencao_iptu_social": [False, False],
        })

        df_res, meta = self.pipeline.executar_inferencia(df_teste, "random_forest_debt_model.joblib")

        self.assertEqual(len(df_res), 2)
        self.assertIn("score_recuperabilidade", df_res.columns)
        self.assertIn("faixa_recuperabilidade", df_res.columns)
        self.assertIn("probabilidade_recuperacao", df_res.columns)
        self.assertIn("probabilidade_inadimplencia", df_res.columns)
        self.assertIn("canal_recomendado", df_res.columns)

        # Registro 1 (recente com bens) deve ter score maior que registro 2 (antigo ajuizado sem bens)
        self.assertGreater(df_res.loc[0, "score_recuperabilidade"], df_res.loc[1, "score_recuperabilidade"])
        self.assertEqual(meta["total_registros_processados"], 2)
        self.assertGreater(meta["tempo_execucao_ms"], 0)

    def test_execucao_inferencia_xgboost(self):
        """Testa a inferência caso o modelo selecionado seja o XGBoost."""
        df_teste = pd.DataFrame({
            "id_devedor": ["DIV-201"],
            "tributo": ["IPTU"],
            "tipo_pessoa": ["Pessoa Física (PF)"],
            "tempo_inscricao_meses": [18],
            "valor_principal": [4500.0],
            "juros_multas": [500.0],
            "valor_total_divida": [5000.0],
            "quantidade_debitos": [2],
            "historico_parcelamentos": [1],
            "execucao_ajuizada": ["Não"],
            "possui_bens": ["Sim"],
            "contato_atualizado": ["Sim"],
            "faixa_renda": ["2 a 5 SM"],
            "regiao": ["Plano Diretor Norte"],
            "isencao_iptu_social": [False],
        })

        df_res, meta = self.pipeline.executar_inferencia(df_teste, "xgboost_debt_model.joblib")
        self.assertEqual(len(df_res), 1)
        self.assertEqual(meta["modelo_utilizado"], "xgboost_debt_model.joblib")
        self.assertTrue(5.0 <= df_res.loc[0, "score_recuperabilidade"] <= 99.0)

    def test_priorizacao_fila_cobranca_heap_maximo(self):
        """Verifica a priorização O(log n) com exclusão automática de beneficiários do IPTU Social."""
        df_sim = pd.DataFrame({
            "id_devedor": ["DIV-A", "DIV-B (Social)", "DIV-C"],
            "inscricao_imobiliaria": ["IMP-01", "IMP-02", "IMP-03"],
            "score_recuperabilidade": [85.0, 92.0, 60.0],
            "valor_total_divida": [3000.0, 1500.0, 8000.0],
            "isencao_iptu_social": [False, True, False],  # DIV-B é social!
        })

        ranking = self.pipeline.priorizar_fila_cobranca(df_sim)

        # DIV-B não deve estar presente no ranking preditivo de cobrança
        ids_no_ranking = [r["id_divida"] for r in ranking]
        self.assertIn("DIV-A", ids_no_ranking)
        self.assertIn("DIV-C", ids_no_ranking)
        self.assertNotIn("DIV-B (Social)", ids_no_ranking)

        # O primeiro da fila deve ser DIV-A (score 85.0)
        self.assertEqual(ranking[0]["id_divida"], "DIV-A")
        self.assertEqual(ranking[0]["score_recuperabilidade"], 85.0)

    def test_singleton_retorna_mesma_instancia(self):
        p1 = get_pipeline_inferencia_singleton()
        p2 = get_pipeline_inferencia_singleton()
        self.assertIs(p1, p2)


if __name__ == "__main__":
    unittest.main()
