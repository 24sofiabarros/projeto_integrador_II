"""
Módulo de Coleta de Dados via API REST (SITRIB - Sefin Palmas-TO).
Implementação da Tarefa E1 - Sprint 3 (Pipeline ETL).
"""

from .coleta_api import (
    ColetorAPISefin,
    anonimizar_cpf,
    anonimizar_cnpj,
    anonimizar_registro_lgpd,
    AutenticacaoInvalidaError,
    AcessoNegadoError,
    RateLimitExcedidoError,
    ColetaAPIError,
)

__all__ = [
    "ColetorAPISefin",
    "anonimizar_cpf",
    "anonimizar_cnpj",
    "anonimizar_registro_lgpd",
    "AutenticacaoInvalidaError",
    "AcessoNegadoError",
    "RateLimitExcedidoError",
    "ColetaAPIError",
]
