"""
========================================================================================
Testes Automatizados para o Módulo de Scoring de Recuperabilidade (Sprint 4 - SITRIB)
Integrante: Hyag Herrcolis Silva Queiroz
Validação de:
  1. Limites do Score [0.0 a 100.0] e consistência matemática.
  2. Diferenciação rigorosa entre P(inadimplência) e P(recuperação).
  3. Classificação nas 3 Faixas Operacionais (Alta, Média, Baixa).
  4. Regra de proteção social ao IPTU Social (não agressão a vulneráveis).
  5. Tratamento de valores faltantes (NaN, None, tipos inválidos).
  6. Decomposição explicável de fatores para interpretabilidade fazendária.
  7. Processamento vetorizado em lote (DataFrames).
========================================================================================
"""

import math
import unittest
import numpy as np
import pandas as pd

from src.scoring.recuperabilidade import (
    ScoringRecuperabilidade,
    ResultadoScoring,
    FaixaRecuperabilidade,
    calcular_score_lote,
)


class TestScoringRecuperabilidade(unittest.TestCase):
    """Testes unitários para o motor de scoring de recuperabilidade da SEFIN Palmas."""

    def setUp(self):
        self.engine = ScoringRecuperabilidade()

    def test_inicializacao_parametros_validos(self):
        eng = ScoringRecuperabilidade(peso_ml=0.6, peso_material=0.4, limiar_alta=70.0, limiar_media=45.0)
        self.assertEqual(eng.peso_ml, 0.6)
        self.assertEqual(eng.peso_material, 0.4)
        self.assertEqual(eng.limiar_alta, 70.0)
        self.assertEqual(eng.limiar_media, 45.0)

    def test_inicializacao_pesos_invalidos_levanta_erro(self):
        with self.assertRaises(ValueError):
            ScoringRecuperabilidade(peso_ml=0.7, peso_material=0.5)  # Soma = 1.2 != 1.0

    def test_inicializacao_limiares_invalidos_levanta_erro(self):
        with self.assertRaises(ValueError):
            ScoringRecuperabilidade(limiar_alta=40.0, limiar_media=50.0)  # Alta <= Media

    def test_score_alta_recuperabilidade(self):
        """Caso favorável: débito recente, valor moderado, bens penhoráveis, contato ativo e alta probabilidade."""
        res = self.engine.calcular_score_individual(
            probabilidade_recuperacao=0.92,
            tempo_inscricao_meses=6.0,
            valor_total_divida=3500.0,
            possui_bens="Sim",
            contato_atualizado="Sim",
            historico_parcelamentos=1,
            execucao_ajuizada="Não",
            faixa_renda="5 a 10 SM",
            isencao_iptu_social=False,
        )
        self.assertIsInstance(res, ResultadoScoring)
        self.assertGreaterEqual(res.score, 68.0)
        self.assertEqual(res.faixa, FaixaRecuperabilidade.ALTA)
        self.assertIn("Digital", res.canal_recomendado)
        self.assertFalse(res.bloqueio_cobranca_social)

    def test_score_baixa_recuperabilidade(self):
        """Caso crítico: débito antigo (> 5 anos), sem bens, sem contato, sem histórico e baixa probabilidade."""
        res = self.engine.calcular_score_individual(
            probabilidade_recuperacao=0.10,
            tempo_inscricao_meses=68.0,
            valor_total_divida=180000.0,
            possui_bens="Não",
            contato_atualizado="Não",
            historico_parcelamentos=0,
            execucao_ajuizada="Sim",
            faixa_renda="Até 2 SM",
            isencao_iptu_social=False,
        )
        self.assertLess(res.score, 42.0)
        self.assertEqual(res.faixa, FaixaRecuperabilidade.BAIXA)
        self.assertIn("Execução Fiscal", res.canal_recomendado)

    def test_score_media_recuperabilidade(self):
        """Caso intermediário: probabilidade média, maturidade moderada."""
        res = self.engine.calcular_score_individual(
            probabilidade_recuperacao=0.52,
            tempo_inscricao_meses=30.0,
            valor_total_divida=12000.0,
            possui_bens="Não",
            contato_atualizado="Sim",
            historico_parcelamentos=1,
            execucao_ajuizada="Não",
            faixa_renda="2 a 5 SM",
            isencao_iptu_social=False,
        )
        self.assertGreaterEqual(res.score, 42.0)
        self.assertLess(res.score, 68.0)
        self.assertEqual(res.faixa, FaixaRecuperabilidade.MEDIA)
        self.assertIn("Protesto", res.canal_recomendado)

    def test_diferenciacao_probabilidade_inadimplencia_vs_recuperacao(self):
        """Verifica se P(inadimplência) + P(recuperação) == 1.0 rigorosamente."""
        p_recup = 0.735
        res = self.engine.calcular_score_individual(
            probabilidade_recuperacao=p_recup,
            tempo_inscricao_meses=18.0,
            valor_total_divida=5000.0,
        )
        self.assertAlmostEqual(res.probabilidade_recuperacao, p_recup, places=3)
        self.assertAlmostEqual(res.probabilidade_inadimplencia, 1.0 - p_recup, places=3)
        self.assertAlmostEqual(res.probabilidade_recuperacao + res.probabilidade_inadimplencia, 1.0, places=4)

    def test_regra_protecao_iptu_social(self):
        """Contribuinte isento do IPTU Social deve receber proteção com bloqueio de cobrança agressiva."""
        res = self.engine.calcular_score_individual(
            probabilidade_recuperacao=0.88,  # Mesmo com propensão estatística alta
            tempo_inscricao_meses=8.0,
            valor_total_divida=1200.0,
            isencao_iptu_social=True,        # Beneficiário Social
        )
        self.assertTrue(res.bloqueio_cobranca_social)
        self.assertLessEqual(res.score, 25.0)
        self.assertEqual(res.faixa, FaixaRecuperabilidade.BAIXA)
        self.assertIn("Proteção Social", res.canal_recomendado)

    def test_tratamento_valores_ausentes_e_extremos(self):
        """Garante resiliência e ausência de exceções quando houver NaNs ou valores fora da faixa."""
        res = self.engine.calcular_score_individual(
            probabilidade_recuperacao=float("nan"),
            tempo_inscricao_meses=float("nan"),
            valor_total_divida=float("nan"),
            possui_bens=None,
            contato_atualizado=None,
            historico_parcelamentos=None,
            execucao_ajuizada=None,
            faixa_renda=None,
        )
        self.assertFalse(math.isnan(res.score))
        self.assertGreaterEqual(res.score, 0.0)
        self.assertLessEqual(res.score, 100.0)
        self.assertIn(res.faixa, [FaixaRecuperabilidade.ALTA, FaixaRecuperabilidade.MEDIA, FaixaRecuperabilidade.BAIXA])

    def test_interpretabilidade_decomposicao_fatores(self):
        """Verifica se os fatores de contribuição estão presentes e explicáveis."""
        res = self.engine.calcular_score_individual(
            probabilidade_recuperacao=0.80,
            tempo_inscricao_meses=12.0,
            valor_total_divida=4000.0,
            possui_bens="Sim",
            contato_atualizado="Sim",
            historico_parcelamentos=1,
            faixa_renda="5 a 10 SM",
        )
        fatores = res.fatores_contribuicao
        self.assertIn("contribuicao_modelo_ia", fatores)
        self.assertIn("contribuicao_antiguidade", fatores)
        self.assertIn("contribuicao_valor_divida", fatores)
        self.assertIn("contribuicao_garantias_contato", fatores)
        self.assertIn("contribuicao_capacidade_renda", fatores)

        for nome, valor in fatores.items():
            self.assertGreaterEqual(valor, 0.0, f"Fator {nome} negativo: {valor}")

    def test_calcular_score_lote_dataframe(self):
        """Testa o processamento vetorizado sobre DataFrame com múltiplos registros."""
        df_teste = pd.DataFrame({
            "id_devedor": ["D1", "D2", "D3"],
            "tempo_inscricao_meses": [6, 36, 72],
            "valor_total_divida": [2500.0, 15000.0, 200000.0],
            "possui_bens": ["Sim", "Não", "Não"],
            "contato_atualizado": ["Sim", "Sim", "Não"],
            "historico_parcelamentos": [1, 2, 0],
            "execucao_ajuizada": ["Não", "Não", "Sim"],
            "faixa_renda": ["Acima de 10 SM", "2 a 5 SM", "Até 2 SM"],
            "isencao_iptu_social": [False, False, False]
        })
        probs = [0.90, 0.55, 0.12]

        df_out = calcular_score_lote(df_teste, probs, self.engine)

        self.assertEqual(len(df_out), 3)
        self.assertIn("score_recuperabilidade", df_out.columns)
        self.assertIn("faixa_recuperabilidade", df_out.columns)
        self.assertIn("canal_recomendado", df_out.columns)
        self.assertIn("probabilidade_inadimplencia", df_out.columns)
        self.assertIn("probabilidade_recuperacao", df_out.columns)

        # Registro 1 deve ter score maior que o 2, que deve ser maior que o 3
        self.assertGreater(df_out.loc[0, "score_recuperabilidade"], df_out.loc[1, "score_recuperabilidade"])
        self.assertGreater(df_out.loc[1, "score_recuperabilidade"], df_out.loc[2, "score_recuperabilidade"])


if __name__ == "__main__":
    unittest.main()
