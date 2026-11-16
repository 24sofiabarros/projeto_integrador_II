"""
========================================================================================
Módulo: Pipeline de Carregamento de Modelos Serializados e Inferência Preditiva
Projeto Integrador Eixo II — BIINAR / Universidade Federal do Tocantins (UFT)
Cliente / Órgão: Secretaria Municipal de Finanças de Palmas (SEFIN Palmas-TO)
Etapa: Sprint 4 — Modelo de IA e MVP (Entregáveis E2 e E3)
Integrante Responsável: Hyag Herrcolis Silva Queiroz

RESPONSABILIDADES E ARQUITETURA:
  1. GerenciadorModelos: Localização, integridade (SHA-256), carregamento e cache dos
     modelos serializados em /models (.joblib e .pkl).
  2. Validação e Pré-processamento: Checagem de schema, tipos e imputação defensiva de
     atributos ausentes antes da entrada no modelo.
  3. Inferência de Probabilidades: Extração rigorosa de P(recuperável) = probs[:, 1].
  4. Encaminhamento ao Scoring: Alimentação do motor de scoring de recuperabilidade.
  5. Integração com FilaCobrancaHeap: Priorização O(log n) com Heap Máximo excluindo
     automaticamente contribuintes vulneráveis do IPTU Social.
========================================================================================
"""

from __future__ import annotations

import glob
import hashlib
import io
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd

from src.scoring.recuperabilidade import (
    ScoringRecuperabilidade,
    ResultadoScoring,
    FaixaRecuperabilidade,
    calcular_score_lote,
)
from src.estruturas.arquitetura_dados import FilaCobrancaHeap

log = logging.getLogger("sitrib_pipeline")
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


# ======================================================================================
# EXCEÇÕES CUSTOMIZADAS DO PIPELINE
# ======================================================================================

class PipelineError(Exception):
    """Exceção base do pipeline da SEFIN."""
    pass


class ModeloNaoEncontradoError(PipelineError):
    """Lançada quando o artefato serializado não existe no diretório /models."""
    pass


class ModeloCorrompidoError(PipelineError):
    """Lançada quando o arquivo do modelo está corrompido ou ilegível."""
    pass


class ModeloInvalidoError(PipelineError):
    """Lançada quando o objeto carregado não é um pipeline ou classificador compatível."""
    pass


class DadosIncompativeisError(PipelineError):
    """Lançada quando os dados de entrada violam requisitos mínimos e não podem ser saneados."""
    pass


# ======================================================================================
# 1. GERENCIADOR DE ARTEFATOS SERIALIZADOS (/models)
# ======================================================================================

class GerenciadorModelos:
    """
    Gerencia localização, verificação de integridade e carregamento em memória (cache)
    dos modelos de Machine Learning treinados por Sofia.
    """

    MODELO_CAMPEAO_DEFAULT = "random_forest_debt_model.joblib"

    def __init__(self, models_dir: Optional[Union[str, Path]] = None):
        if models_dir is None:
            # Diretório raiz do projeto / models
            raiz = Path(__file__).resolve().parents[2]
            self.models_dir = raiz / "models"
        else:
            self.models_dir = Path(models_dir)

        self._cache_modelos: Dict[str, Any] = {}
        self._cache_hashes: Dict[str, str] = {}

    def _calcular_hash(self, file_path: Path) -> str:
        """Calcula o hash SHA-256 do arquivo para auditoria de integridade."""
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha.update(chunk)
        return sha.hexdigest()

    def listar_modelos_disponiveis(self) -> List[Dict[str, Any]]:
        """
        Lista todos os modelos (.joblib e .pkl) presentes em /models,
        retornando nome, caminho, tamanho e hash de integridade.
        """
        if not self.models_dir.exists():
            return []

        padroes = ["*.joblib", "*.pkl"]
        arquivos: List[Path] = []
        for p in padroes:
            arquivos.extend(self.models_dir.glob(p))

        # Ordenar colocando o campeão primeiro
        arquivos = sorted(arquivos, key=lambda p: (0 if p.name == self.MODELO_CAMPEAO_DEFAULT else 1, p.name))

        modelos_info = []
        for arq in arquivos:
            try:
                tamanho_kb = round(arq.stat().st_size / 1024, 1)
                h = self._calcular_hash(arq)[:12]  # Hash truncado para exibição
                modelos_info.append({
                    "nome_arquivo": arq.name,
                    "caminho_completo": str(arq),
                    "tamanho_kb": tamanho_kb,
                    "hash_sha256": h,
                    "is_campeao": (arq.name == self.MODELO_CAMPEAO_DEFAULT),
                })
            except Exception as e:
                log.warning(f"Não foi possível ler metadados de {arq.name}: {e}")

        return modelos_info

    def carregar_modelo(self, nome_ou_caminho: Optional[str] = None) -> Any:
        """
        Carrega o modelo solicitado aplicando cache em memória.
        Se nenhum nome for passado, carrega o modelo campeão padrão.
        """
        if nome_ou_caminho is None or str(nome_ou_caminho).strip() == "":
            nome_ou_caminho = self.MODELO_CAMPEAO_DEFAULT

        caminho = Path(nome_ou_caminho)
        if not caminho.is_absolute():
            caminho = self.models_dir / caminho

        nome_chave = caminho.name

        # Verifica cache em memória
        if nome_chave in self._cache_modelos:
            return self._cache_modelos[nome_chave]

        if not caminho.exists():
            raise ModeloNaoEncontradoError(
                f"O arquivo de modelo '{nome_chave}' não foi encontrado em {self.models_dir}."
            )

        try:
            modelo = joblib.load(caminho)
        except Exception as e:
            raise ModeloCorrompidoError(
                f"Falha ao desserializar o modelo '{nome_chave}': {e}"
            )

        # Validação de compatibilidade técnica
        if not hasattr(modelo, "predict"):
            raise ModeloInvalidoError(
                f"O objeto serializado em '{nome_chave}' não implementa o método 'predict'."
            )

        # Armazena em cache
        self._cache_modelos[nome_chave] = modelo
        try:
            self._cache_hashes[nome_chave] = self._calcular_hash(caminho)
        except Exception:
            pass

        log.info(f"Modelo '{nome_chave}' carregado em memória com sucesso.")
        return modelo

    def carregar_metricas_auditoria(self) -> Optional[Dict[str, Any]]:
        """Carrega o relatório JSON de métricas de teste gerado em /models."""
        caminho_json = self.models_dir / "model_metrics.json"
        if not caminho_json.exists():
            return None
        try:
            with open(caminho_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"Erro ao carregar métricas de auditoria: {e}")
            return None


# ======================================================================================
# 2. PIPELINE DE INFERÊNCIA E INTEGRAÇÃO DE SCORING
# ======================================================================================

class PipelineInferencia:
    """
    Pipeline ponta a ponta que recebe dados tabulares, realiza a validação de schema,
    imputação de contingência, executa a inferência nos modelos scikit-learn/XGBoost,
    extrai a probabilidade de recuperação e calcula o Score de Recuperabilidade.
    """

    # Schema oficial esperado pelos modelos treinados
    FEATURES_NUMERICAS = [
        "tempo_inscricao_meses",
        "valor_principal",
        "juros_multas",
        "valor_total_divida",
        "quantidade_debitos",
        "historico_parcelamentos",
    ]

    FEATURES_CATEGORICAS = [
        "tributo",
        "tipo_pessoa",
        "execucao_ajuizada",
        "possui_bens",
        "contato_atualizado",
        "faixa_renda",
        "regiao",
    ]

    TODAS_FEATURES = FEATURES_NUMERICAS + FEATURES_CATEGORICAS

    def __init__(
        self,
        gerenciador_modelos: Optional[GerenciadorModelos] = None,
        motor_scoring: Optional[ScoringRecuperabilidade] = None,
    ):
        self.gerenciador = gerenciador_modelos or GerenciadorModelos()
        self.scoring = motor_scoring or ScoringRecuperabilidade()

    def validar_e_sanear_dados(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Valida o schema de entrada e aplica imputação segura para features faltantes,
        garantindo integridade para o ColumnTransformer sem risco de vazamento de dados.
        """
        if df is None or len(df) == 0:
            raise DadosIncompativeisError("O DataFrame fornecido para inferência está vazio.")

        df_san = df.copy()

        # 1. Ajustes e inferências de valores financeiros
        if "valor_total_divida" not in df_san.columns:
            if "valor_principal" in df_san.columns:
                v_princ = pd.to_numeric(df_san["valor_principal"], errors="coerce").fillna(1000.0)
                if "juros_multas" in df_san.columns:
                    v_juros = pd.to_numeric(df_san["juros_multas"], errors="coerce").fillna(0.0)
                else:
                    v_juros = 0.0
                df_san["valor_total_divida"] = v_princ + v_juros
            elif "valor" in df_san.columns:
                df_san["valor_total_divida"] = pd.to_numeric(df_san["valor"], errors="coerce").fillna(1000.0)
                df_san["valor_principal"] = df_san["valor_total_divida"] * 0.8
                df_san["juros_multas"] = df_san["valor_total_divida"] * 0.2
            else:
                df_san["valor_total_divida"] = 1000.0
                df_san["valor_principal"] = 800.0
                df_san["juros_multas"] = 200.0

        if "valor_principal" not in df_san.columns:
            df_san["valor_principal"] = df_san["valor_total_divida"] * 0.8
        if "juros_multas" not in df_san.columns:
            df_san["juros_multas"] = df_san["valor_total_divida"] - df_san["valor_principal"]

        # 2. Imputação de features numéricas ausentes
        defaults_num = {
            "tempo_inscricao_meses": 24.0,
            "quantidade_debitos": 1,
            "historico_parcelamentos": 0,
        }
        for col, val_padrao in defaults_num.items():
            if col not in df_san.columns:
                df_san[col] = val_padrao
            else:
                df_san[col] = pd.to_numeric(df_san[col], errors="coerce").fillna(val_padrao)

        # 3. Imputação de features categóricas ausentes
        defaults_cat = {
            "tributo": "IPTU",
            "tipo_pessoa": "Pessoa Física (PF)",
            "execucao_ajuizada": "Não",
            "possui_bens": "Não",
            "contato_atualizado": "Sim",
            "faixa_renda": "2 a 5 SM",
            "regiao": "Plano Diretor Sul",
        }
        for col, val_padrao in defaults_cat.items():
            if col not in df_san.columns:
                df_san[col] = val_padrao
            else:
                df_san[col] = df_san[col].fillna(val_padrao).astype(str)

        # Garante tipos corretos
        for col in self.FEATURES_NUMERICAS:
            df_san[col] = pd.to_numeric(df_san[col], errors="coerce").fillna(0.0)

        for col in self.FEATURES_CATEGORICAS:
            df_san[col] = df_san[col].astype(str)

        return df_san

    def executar_inferencia(
        self,
        df: pd.DataFrame,
        nome_modelo: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Executa o pipeline completo de inferência:
          1. Saneamento dos dados;
          2. Carregamento do modelo serializado;
          3. Predição de probabilidades de recuperação;
          4. Cálculo do Score de Recuperabilidade e Faixas Operacionais;
          5. Consolidação de metadados de execução.
        """
        inicio = time.time()
        df_san = self.validar_e_sanear_dados(df)

        # Carrega o modelo
        modelo = self.gerenciador.carregar_modelo(nome_modelo)
        nome_efetivo = nome_modelo or self.gerenciador.MODELO_CAMPEAO_DEFAULT

        # Extração de features para a inferência
        X_input = df_san[self.TODAS_FEATURES]

        # Execução da inferência probabilística
        if hasattr(modelo, "predict_proba"):
            probs_matrix = modelo.predict_proba(X_input)
            classes = list(getattr(modelo, "classes_", [0, 1]))
            if 1 in classes:
                idx_classe_1 = classes.index(1)
                probs_recup = probs_matrix[:, idx_classe_1]
            else:
                probs_recup = probs_matrix[:, -1]
        else:
            # Fallback para modelos que só produzem predição binária direta
            preds = modelo.predict(X_input)
            probs_recup = np.where(preds == 1, 0.75, 0.25)

        # Encaminhamento para o Motor de Scoring
        df_resultado = calcular_score_lote(
            df=df_san,
            probabilidades_recuperacao=probs_recup,
            engine=self.scoring,
        )

        duracao_ms = round((time.time() - inicio) * 1000, 2)

        # Metadados de Auditoria da Inferência
        resumo_faixas = df_resultado["faixa_recuperabilidade"].value_counts().to_dict()
        metadados = {
            "modelo_utilizado": nome_efetivo,
            "total_registros_processados": len(df_resultado),
            "tempo_execucao_ms": duracao_ms,
            "distribuicao_faixas": resumo_faixas,
            "score_medio": round(float(df_resultado["score_recuperabilidade"].mean()), 2),
            "probabilidade_recuperacao_media": round(float(df_resultado["probabilidade_recuperacao"].mean()), 4),
            "total_casos_protecao_social": int(df_resultado.get("bloqueio_cobranca_social", False).sum()),
        }

        return df_resultado, metadados

    def priorizar_fila_cobranca(self, df_resultado: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Integração com a FilaCobrancaHeap de src/estruturas/arquitetura_dados.py.
        Organiza os débitos em Heap Máximo priorizando os maiores scores de recuperabilidade
        e excluindo automaticamente beneficiários do IPTU Social.
        """
        fila = FilaCobrancaHeap()

        for _, row in df_resultado.iterrows():
            score = float(row["score_recuperabilidade"])
            id_divida = str(row.get("id_devedor", row.get("numero_cda", "DIV-UNKNOWN")))
            inscricao = str(row.get("inscricao_imobiliaria", row.get("bairro_setor", "SIT-PMW")))
            valor = float(row["valor_total_divida"])
            iptu_social = bool(row.get("isencao_iptu_social", row.get("bloqueio_cobranca_social", False)))

            fila.inserir_divida(
                score=score,
                id_divida=id_divida,
                inscricao=inscricao,
                valor=valor,
                iptu_social=iptu_social,
            )

        ranking_priorizado = []
        posicao = 1
        while item := fila.extrair_proxima_cobranca():
            score, id_divida, inscricao, valor = item
            ranking_priorizado.append({
                "posicao": posicao,
                "score_recuperabilidade": score,
                "id_divida": id_divida,
                "inscricao_ou_local": inscricao,
                "valor_total_divida": valor,
            })
            posicao += 1

        return ranking_priorizado


# Singleton para uso simplificado no backend Streamlit
_pipeline_singleton: Optional[PipelineInferencia] = None

def get_pipeline_inferencia_singleton() -> PipelineInferencia:
    """Retorna a instância única em cache do pipeline para evitar recarregamentos no Streamlit."""
    global _pipeline_singleton
    if _pipeline_singleton is None:
        _pipeline_singleton = PipelineInferencia()
    return _pipeline_singleton
