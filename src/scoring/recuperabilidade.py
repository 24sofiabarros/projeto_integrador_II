"""
========================================================================================
Módulo: Scoring de Recuperabilidade de Créditos Tributários
Projeto Integrador Eixo II — BIINAR / Universidade Federal do Tocantins (UFT)
Cliente / Órgão: Secretaria Municipal de Finanças de Palmas (SEFIN Palmas-TO)
Etapa: Sprint 4 — Modelo de IA e MVP (Entregáveis E2 e E3)
Integrante Responsável: Hyag Herrcolis Silva Queiroz

FUNDAMENTAÇÃO METODOLÓGICA:
O Score de Recuperabilidade transforma as estimativas probabilísticas de adimplemento
geradas pelos modelos preditivos (Random Forest / XGBoost / Baselines) e as características
materiais do crédito tributário em um indicador sintético padronizado de 0 a 100, segmentado
em três faixas operacionais para priorização fazendária:
  - Alta Recuperabilidade: Score >= 68.0
  - Média Recuperabilidade: 42.0 <= Score < 68.0
  - Baixa Recuperabilidade: Score < 42.0

DIFERENCIAÇÃO CONCEITUAL OBRIGATÓRIA:
  1. Probabilidade de Inadimplência P(inad): Chance de o débito permanecer não pago.
  2. Probabilidade de Recuperação P(recup): Chance de adimplemento/recuperação = 1 - P(inad).
  3. Score de Recuperabilidade (0 a 100): Combinação multivariada de P(recup), antiguidade,
     valor do débito, capacidade contributiva territorial e garantias de solvência.
  4. Faixa de Priorização: Regra de encaminhamento operacional para a fiscalização da SEFIN.
========================================================================================
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


class FaixaRecuperabilidade(str, enum.Enum):
    """Categorias operacionais de priorização de cobrança na SEFIN Palmas."""
    ALTA = "Alta"
    MEDIA = "Média"
    BAIXA = "Baixa"


@dataclass
class ResultadoScoring:
    """Estrutura rica de resposta contendo score, faixa, métricas e interpretabilidade."""
    score: float
    faixa: FaixaRecuperabilidade
    probabilidade_recuperacao: float
    probabilidade_inadimplencia: float
    canal_recomendado: str
    fatores_contribuicao: Dict[str, float] = field(default_factory=dict)
    bloqueio_cobranca_social: bool = False
    justificativa_operacional: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score_recuperabilidade": round(self.score, 1),
            "faixa_recuperabilidade": self.faixa.value,
            "probabilidade_recuperacao": round(self.probabilidade_recuperacao, 4),
            "probabilidade_inadimplencia": round(self.probabilidade_inadimplencia, 4),
            "canal_recomendado": self.canal_recomendado,
            "fatores_contribuicao": {k: round(v, 2) for k, v in self.fatores_contribuicao.items()},
            "bloqueio_cobranca_social": self.bloqueio_cobranca_social,
            "justificativa_operacional": self.justificativa_operacional,
        }


class ScoringRecuperabilidade:
    """
    Motor de Scoring de Recuperabilidade de Dívida Ativa da SEFIN Palmas.
    
    Combina a probabilidade estimada do modelo de Machine Learning com
    fatores determinísticos legais, materiais e socioeconômicos.
    """

    # Limiares das Faixas Operacionais (Calibrados conforme estudo empírico fazendário)
    LIMIAR_ALTA = 68.0
    LIMIAR_MEDIA = 42.0

    # Pesos dos macrocomponentes do Score (Soma = 1.0)
    PESO_ML = 0.50        # 50% propensão preditiva estatística
    PESO_MATERIAL = 0.50  # 50% atributos materiais objetivos da dívida

    # Subpesos da camada material (Soma = 1.0)
    PESO_TEMPO = 0.30     # Antiguidade do crédito (risco prescricional - Art. 174 CTN)
    PESO_VALOR = 0.25     # Faixa de valor consolidado e custo de cobrança
    PESO_GARANTIA = 0.25  # Bens penhoráveis, contatos válidos e parcelamentos
    PESO_RENDA = 0.20     # Capacidade contributiva socioeconômica setorial (IBGE)

    def __init__(
        self,
        peso_ml: float = PESO_ML,
        peso_material: float = PESO_MATERIAL,
        limiar_alta: float = LIMIAR_ALTA,
        limiar_media: float = LIMIAR_MEDIA,
    ):
        if not math.isclose(peso_ml + peso_material, 1.0, rel_tol=1e-5):
            raise ValueError(f"A soma dos pesos (peso_ml={peso_ml} + peso_material={peso_material}) deve ser exatamente 1.0.")
        if limiar_alta <= limiar_media:
            raise ValueError("O limiar de Alta recuperabilidade deve ser estritamente maior que o de Média recuperabilidade.")

        self.peso_ml = peso_ml
        self.peso_material = peso_material
        self.limiar_alta = limiar_alta
        self.limiar_media = limiar_media

    def _calcular_fator_tempo(self, meses_inscricao: float) -> float:
        """
        Calcula o subfator de antiguidade do crédito [0.0 a 100.0].
        Débitos recentes (< 12 meses) têm máxima recuperabilidade.
        Após 60 meses (5 anos), incide risco prescricional (Art. 174 CTN).
        """
        if math.isnan(meses_inscricao) or meses_inscricao < 0:
            meses_inscricao = 24.0  # Mediana de contingência

        # Decaimento linear suavizado até o limite prescricional de 60 meses
        fator = 100.0 - (meses_inscricao / 60.0) * 85.0
        return float(np.clip(fator, 5.0, 100.0))

    def _calcular_fator_valor(self, valor_total: float) -> float:
        """
        Calcula o subfator de valor [0.0 a 100.0].
        - Valores entre R$ 800 e R$ 15.000: alta liquidez administrativa e custo equilibrado.
        - Valores muito baixos (< R$ 300): desvantagem pelo custo de cobrança física.
        - Valores muito elevados (> R$ 100.000): exigem negociação prolongada/judicial.
        """
        if math.isnan(valor_total) or valor_total <= 0:
            return 50.0

        if valor_total <= 500.0:
            return 60.0  # Débito muito pequeno, atende via notificação passiva
        elif valor_total <= 5000.0:
            return 90.0  # Faixa ótima para liquidação rápida
        elif valor_total <= 25000.0:
            return 80.0  # Médio porte com boa resposta a Refis
        elif valor_total <= 100000.0:
            return 65.0  # Porte considerável, negociação requer garantias
        else:
            return 45.0  # Grande devedor, alta litigiosidade

    def _calcular_fator_garantias(
        self,
        possui_bens: str,
        contato_atualizado: str,
        historico_parcelamentos: int,
        execucao_ajuizada: str,
    ) -> float:
        """
        Calcula o subfator de garantias e cooperatividade [0.0 a 100.0].
        """
        pontos = 50.0  # Ponto neutro

        # Contato ativo viabiliza comunicação digital
        if str(contato_atualizado).strip().lower() in ["sim", "true", "1", "s"]:
            pontos += 15.0
        else:
            pontos -= 15.0

        # Bens penhoráveis conferem lastro real à execução
        if str(possui_bens).strip().lower() in ["sim", "true", "1", "s"]:
            pontos += 20.0
        else:
            pontos -= 10.0

        # Histórico de adesão prévia demonstra propensão a acordos
        try:
            parc = int(historico_parcelamentos)
            if parc > 0:
                pontos += min(15.0, parc * 7.5)
        except (ValueError, TypeError):
            pass

        # Execução ajuizada sem bens penhoráveis indica litígio improdutivo
        if str(execucao_ajuizada).strip().lower() in ["sim", "true", "1", "s"]:
            if str(possui_bens).strip().lower() not in ["sim", "true", "1", "s"]:
                pontos -= 20.0
            else:
                pontos += 5.0  # Já ajuizado com penhora em andamento

        return float(np.clip(pontos, 0.0, 100.0))

    def _calcular_fator_renda(self, faixa_renda: str) -> float:
        """
        Calcula a capacidade contributiva com base na faixa socioeconômica [0.0 a 100.0].
        """
        fr = str(faixa_renda).strip().lower()
        if "acima de 10" in fr or "> 10" in fr:
            return 90.0
        elif "5 a 10" in fr:
            return 75.0
        elif "2 a 5" in fr:
            return 55.0
        elif "até 2" in fr or "<= 2" in fr:
            return 35.0
        else:
            return 50.0  # Neutro para dados não informados

    def calcular_score_individual(
        self,
        probabilidade_recuperacao: float,
        tempo_inscricao_meses: float,
        valor_total_divida: float,
        possui_bens: str = "Não",
        contato_atualizado: str = "Sim",
        historico_parcelamentos: int = 0,
        execucao_ajuizada: str = "Não",
        faixa_renda: str = "2 a 5 SM",
        isencao_iptu_social: bool = False,
    ) -> ResultadoScoring:
        """
        Calcula o score de recuperabilidade completo para um único registro.
        
        Parâmetros:
            probabilidade_recuperacao: float [0.0 a 1.0] extraída do modelo de ML.
            tempo_inscricao_meses: idade da dívida ativa em meses.
            valor_total_divida: montante total consolidado (principal + encargos).
            possui_bens: "Sim" ou "Não" para patrimônio penhorável localizado.
            contato_atualizado: "Sim" ou "Não" para telefone/e-mail/endereço válidos.
            historico_parcelamentos: quantidade de acordos ou adesões prévias.
            execucao_ajuizada: "Sim" ou "Não" para processo judicial instaurado.
            faixa_renda: faixa de renda domiciliar setorial (Censo IBGE / Palmas).
            isencao_iptu_social: booleano de proteção social ao contribuinte vulnerável.
        """
        # Validação e saneamento de probabilidades
        if probabilidade_recuperacao is None or math.isnan(probabilidade_recuperacao):
            p_recup = 0.50
        else:
            p_recup = float(np.clip(probabilidade_recuperacao, 0.0, 1.0))
        p_inad = float(round(1.0 - p_recup, 4))

        if tempo_inscricao_meses is None or math.isnan(tempo_inscricao_meses):
            tempo_inscricao_meses = 24.0
        if valor_total_divida is None or math.isnan(valor_total_divida):
            valor_total_divida = 5000.0

        # 1. Componente de Machine Learning (0 a 100)
        componente_ml = p_recup * 100.0

        # 2. Subfatores materiais (0 a 100 cada)
        f_tempo = self._calcular_fator_tempo(tempo_inscricao_meses)
        f_valor = self._calcular_fator_valor(valor_total_divida)
        f_garantia = self._calcular_fator_garantias(
            possui_bens=possui_bens,
            contato_atualizado=contato_atualizado,
            historico_parcelamentos=historico_parcelamentos,
            execucao_ajuizada=execucao_ajuizada,
        )
        f_renda = self._calcular_fator_renda(faixa_renda)

        # 3. Agregação da Camada Material
        componente_material = (
            self.PESO_TEMPO * f_tempo +
            self.PESO_VALOR * f_valor +
            self.PESO_GARANTIA * f_garantia +
            self.PESO_RENDA * f_renda
        )

        # 4. Score Base Ponderado
        score_bruto = (self.peso_ml * componente_ml) + (self.peso_material * componente_material)

        # 5. Aplicação de Regras de Negócio e Proteção Social
        bloqueio_social = False
        justificativa = "Score calculado com base em modelo supervisionado e atributos cadastrais objetivos."

        if isencao_iptu_social:
            bloqueio_social = True
            # Contribuinte vulnerável do IPTU Social não deve sofrer cobrança coercitiva agressiva
            score_final = min(score_bruto, 25.0)
            faixa = FaixaRecuperabilidade.BAIXA
            canal = "Proteção Social / Encaminhamento para Revisão de Isenção (IPTU Social)"
            justificativa = "Contribuinte amparado pela política de proteção do IPTU Social. Cobrança coercitiva suspensa."
        else:
            score_final = float(np.clip(score_bruto, 5.0, 99.0))
            if score_final >= self.limiar_alta:
                faixa = FaixaRecuperabilidade.ALTA
                canal = "Cobrança Digital Amigável (WhatsApp / E-mail / DDA)"
                justificativa = "Alta propensão de liquidação rápida e baixo custo de acionamento."
            elif score_final >= self.limiar_media:
                faixa = FaixaRecuperabilidade.MEDIA
                canal = "Protesto Notarial / Notificação Postal / Programa REFIS Palmas"
                justificativa = "Recuperabilidade moderada; indicado para renegociação com condições incentivadas."
            else:
                faixa = FaixaRecuperabilidade.BAIXA
                canal = "Execução Fiscal / Averiguação Patrimonial / Investigação de Insolvência"
                justificativa = "Baixa recuperabilidade ou histórico crítico de inadimplência crônica."

        # Rastreabilidade dos Fatores para Explicabilidade (Interpretabilidade Local)
        fatores = {
            "contribuicao_modelo_ia": self.peso_ml * componente_ml,
            "contribuicao_antiguidade": self.peso_material * self.PESO_TEMPO * f_tempo,
            "contribuicao_valor_divida": self.peso_material * self.PESO_VALOR * f_valor,
            "contribuicao_garantias_contato": self.peso_material * self.PESO_GARANTIA * f_garantia,
            "contribuicao_capacidade_renda": self.peso_material * self.PESO_RENDA * f_renda,
        }

        return ResultadoScoring(
            score=round(score_final, 1),
            faixa=faixa,
            probabilidade_recuperacao=p_recup,
            probabilidade_inadimplencia=p_inad,
            canal_recomendado=canal,
            fatores_contribuicao=fatores,
            bloqueio_cobranca_social=bloqueio_social,
            justificativa_operacional=justificativa,
        )


def calcular_score_lote(
    df: pd.DataFrame,
    probabilidades_recuperacao: Union[np.ndarray, List[float]],
    engine: Optional[ScoringRecuperabilidade] = None,
) -> pd.DataFrame:
    """
    Aplica o motor de scoring a um lote completo (DataFrame), retornando
    as novas colunas calculadas de forma vetorizada e transparente.
    """
    if engine is None:
        engine = ScoringRecuperabilidade()

    if len(df) != len(probabilidades_recuperacao):
        raise ValueError(
            f"Dimensão divergente: DataFrame possui {len(df)} linhas, "
            f"mas foram fornecidas {len(probabilidades_recuperacao)} probabilidades."
        )

    probs = np.asarray(probabilidades_recuperacao, dtype=float)
    scores = []
    faixas = []
    canais = []
    p_inad_list = []
    bloqueios = []

    for idx, (_, row) in enumerate(df.iterrows()):
        p_recup = probs[idx]
        tempo_meses = row.get("tempo_inscricao_meses", 24.0)
        valor_total = row.get("valor_total_divida", row.get("valor_principal", 1000.0))
        possui_bens = row.get("possui_bens", "Não")
        contato = row.get("contato_atualizado", "Sim")
        parc = row.get("historico_parcelamentos", 0)
        ajuizada = row.get("execucao_ajuizada", "Não")
        renda = row.get("faixa_renda", "2 a 5 SM")
        iptu_soc = bool(row.get("isencao_iptu_social", False))

        res = engine.calcular_score_individual(
            probabilidade_recuperacao=p_recup,
            tempo_inscricao_meses=float(tempo_meses) if pd.notna(tempo_meses) else 24.0,
            valor_total_divida=float(valor_total) if pd.notna(valor_total) else 1000.0,
            possui_bens=str(possui_bens) if pd.notna(possui_bens) else "Não",
            contato_atualizado=str(contato) if pd.notna(contato) else "Sim",
            historico_parcelamentos=int(parc) if pd.notna(parc) else 0,
            execucao_ajuizada=str(ajuizada) if pd.notna(ajuizada) else "Não",
            faixa_renda=str(renda) if pd.notna(renda) else "2 a 5 SM",
            isencao_iptu_social=iptu_soc,
        )

        scores.append(res.score)
        faixas.append(res.faixa.value)
        canais.append(res.canal_recomendado)
        p_inad_list.append(res.probabilidade_inadimplencia)
        bloqueios.append(res.bloqueio_cobranca_social)

    df_result = df.copy()
    df_result["score_recuperabilidade"] = scores
    df_result["faixa_recuperabilidade"] = faixas
    df_result["canal_recomendado"] = canais
    df_result["probabilidade_inadimplencia"] = p_inad_list
    df_result["probabilidade_recuperacao"] = np.round(probs, 4)
    df_result["bloqueio_cobranca_social"] = bloqueios

    return df_result
