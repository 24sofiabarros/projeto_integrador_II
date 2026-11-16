"""
========================================================================================
Testes de Integração Ponta a Ponta: Pipeline, Scoring e Backend MVP (Sprint 4)
Integrante: Hyag Herrcolis Silva Queiroz
Projeto: Sistema de Inteligência Tributária (SEFIN Palmas / UFT BIINAR)
========================================================================================
"""

import os
import unittest
import pandas as pd
import numpy as np

from src.pipeline.carregamento_inferencia import (
    get_pipeline_inferencia_singleton,
    GerenciadorModelos,
)
from src.scoring.recuperabilidade import (
    ScoringRecuperabilidade,
    FaixaRecuperabilidade,
)


class TestIntegracaoMVP(unittest.TestCase):
    """Testes de validação integrada entre modelo, pipeline, scoring e painel."""

    @classmethod
    def setUpClass(cls):
        cls.pipeline = get_pipeline_inferencia_singleton()
        data_path = os.path.join(os.path.dirname(__file__), "..", "data", "divida_ativa_palmas.csv")
        if os.path.exists(data_path):
            cls.df_base = pd.read_csv(data_path)
        else:
            raise FileNotFoundError(f"Base de dados não encontrada em {data_path}")

    def test_inferencia_lote_com_base_sefin(self):
        """Valida se o pipeline processa a base real sintética de Palmas sem erros."""
        df_amostra = self.df_base.head(100).copy()
        df_out, meta = self.pipeline.executar_inferencia(df_amostra, "random_forest_debt_model.joblib")

        self.assertEqual(len(df_out), 100)
        self.assertIn("score_recuperabilidade", df_out.columns)
        self.assertIn("faixa_recuperabilidade", df_out.columns)
        self.assertIn("probabilidade_recuperacao", df_out.columns)
        self.assertIn("probabilidade_inadimplencia", df_out.columns)
        self.assertIn("canal_recomendado", df_out.columns)

        # Verifica coerência das faixas
        faixas_encontradas = set(df_out["faixa_recuperabilidade"].unique())
        self.assertTrue(faixas_encontradas.issubset({"Alta", "Média", "Baixa"}))

        # Verifica se todas as probabilidades estão entre 0 e 1
        self.assertTrue((df_out["probabilidade_recuperacao"] >= 0.0).all())
        self.assertTrue((df_out["probabilidade_recuperacao"] <= 1.0).all())

        # Verifica se todos os scores estão entre 0 e 100
        self.assertTrue((df_out["score_recuperabilidade"] >= 0.0).all())
        self.assertTrue((df_out["score_recuperabilidade"] <= 100.0).all())

    def test_alternancia_entre_modelos_serializados(self):
        """Garante que o pipeline pode alternar dinamicamente entre RF, XGBoost e Baselines."""
        df_amostra = self.df_base.head(50).copy()
        
        modelos_para_testar = [
            "random_forest_debt_model.joblib",
            "xgboost_debt_model.joblib",
            "decision_tree_baseline.joblib",
            "logistic_regression_baseline.joblib",
        ]

        for mod_nome in modelos_para_testar:
            with self.subTest(modelo=mod_nome):
                df_out, meta = self.pipeline.executar_inferencia(df_amostra, mod_nome)
                self.assertEqual(meta["modelo_utilizado"], mod_nome)
                self.assertEqual(len(df_out), 50)
                self.assertFalse(df_out["score_recuperabilidade"].isna().any())

    def test_integracao_fila_heap_maximo_com_dados_inferidos(self):
        """Garante que os resultados inferidos alimentam perfeitamente a FilaCobrancaHeap."""
        df_amostra = self.df_base.head(30).copy()
        # Força um dos registros a ter isenção de IPTU Social
        df_amostra.loc[0, "isencao_iptu_social"] = True
        df_amostra.loc[0, "id_devedor"] = "SEFIN-BENEFICIARIO-SOCIAL"

        df_out, _ = self.pipeline.executar_inferencia(df_amostra)
        ranking = self.pipeline.priorizar_fila_cobranca(df_out)

        # O beneficiário social NÃO pode constar na fila de cobrança
        ids_cobranca = [item["id_divida"] for item in ranking]
        self.assertNotIn("SEFIN-BENEFICIARIO-SOCIAL", ids_cobranca)

        # O ranking deve ser estritamente decrescente por score
        scores = [item["score_recuperabilidade"] for item in ranking]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_interpretabilidade_decomposicao_fatores_completa(self):
        """Verifica a decomposição de fatores do score para um contribuinte pontual."""
        engine = self.pipeline.scoring
        res = engine.calcular_score_individual(
            probabilidade_recuperacao=0.85,
            tempo_inscricao_meses=14.0,
            valor_total_divida=3200.0,
            possui_bens="Sim",
            contato_atualizado="Sim",
            historico_parcelamentos=2,
            execucao_ajuizada="Não",
            faixa_renda="5 a 10 SM",
            isencao_iptu_social=False,
        )

        fatores = res.fatores_contribuicao
        self.assertIn("contribuicao_modelo_ia", fatores)
        self.assertIn("contribuicao_antiguidade", fatores)
        self.assertIn("contribuicao_valor_divida", fatores)
        self.assertIn("contribuicao_garantias_contato", fatores)
        self.assertIn("contribuicao_capacidade_renda", fatores)

        # A soma ponderada dos fatores deve ser aproximadamente o score
        soma_fatores = sum(fatores.values())
        self.assertAlmostEqual(res.score, soma_fatores, delta=1.5)


if __name__ == "__main__":
    unittest.main()
