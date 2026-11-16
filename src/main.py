"""
========================================================================================
SITRIB — Sistema de Inteligência Tributária (SEFIN Palmas-TO)
Módulo Principal de Execução e Integração (Sprint 4)
Coordenação: Prof. Dr. David Nadler Prata (UFT • BIINAR)
Equipe Executora: Hyag, Ludmylla, Maiara, Sofia e Vitória
========================================================================================
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Garante path para importações internas
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.pipeline.carregamento_inferencia import (
    get_pipeline_inferencia_singleton,
    GerenciadorModelos,
)
from src.scoring.recuperabilidade import (
    ScoringRecuperabilidade,
    FaixaRecuperabilidade,
)


def main():
    parser = argparse.ArgumentParser(
        description="SITRIB — Sistema de Inteligência Tributária (SEFIN Palmas / UFT BIINAR)"
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Inicia o painel interativo MVP em Streamlit",
    )
    parser.add_argument(
        "--inferencia",
        action="store_true",
        help="Executa inferência em lote na base de dados de Palmas",
    )
    parser.add_argument(
        "--modelo",
        type=str,
        default="random_forest_debt_model.joblib",
        help="Nome do modelo serializado em /models para inferência",
    )
    parser.add_argument(
        "--dados",
        type=str,
        default="data/divida_ativa_palmas.csv",
        help="Caminho do arquivo CSV de dívida ativa para processamento",
    )
    parser.add_argument(
        "--amostra",
        type=int,
        default=5,
        help="Quantidade de linhas de amostra para exibir no terminal",
    )

    args = parser.parse_args()

    if args.dashboard:
        print("🏛️ Iniciando Painel MVP SEFIN Palmas (Streamlit)...")
        app_path = RAIZ / "app.py"
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)])
        return

    print("=" * 80)
    print("🏛️  SITRIB — SECRETARIA MUNICIPAL DE FINANÇAS DE PALMAS (SEFIN-TO)")
    print("    SISTEMA DE INTELIGÊNCIA TRIBUTÁRIA • PRIORIZAÇÃO DA DÍVIDA ATIVA")
    print("=" * 80)

    # 1. Inspeção de Modelos
    gerenciador = GerenciadorModelos()
    modelos = gerenciador.listar_modelos_disponiveis()
    print(f"\n📦 Modelos Preditivos Identificados em /models ({len(modelos)} encontrados):")
    for m in modelos:
        tag = "[CAMPEÃO]" if m["is_campeao"] else "         "
        print(f"  {tag} {m['nome_arquivo']:<38} | {m['tamanho_kb']:>6.1f} KB | SHA-256: {m['hash_sha256']}")

    # 2. Execução de Inferência
    dados_path = RAIZ / args.dados
    if not dados_path.exists():
        print(f"\n❌ Arquivo de dados não encontrado: {dados_path}")
        return

    import pandas as pd
    df_raw = pd.read_csv(dados_path)
    print(f"\n📊 Base de dados carregada: {len(df_raw)} registros de {args.dados}")

    pipeline = get_pipeline_inferencia_singleton()
    print(f"⚙️  Executando pipeline de inferência com modelo: {args.modelo}...")
    df_resultado, metadados = pipeline.executar_inferencia(df_raw, args.modelo)

    print(f"\n✅ Inferência concluída com sucesso em {metadados['tempo_execucao_ms']} ms!")
    print(f"   - Score Médio de Recuperabilidade: {metadados['score_medio']:.1f} / 100")
    print(f"   - Probabilidade Média de Recuperação: {metadados['probabilidade_recuperacao_media']*100:.1f}%")
    print("   - Distribuição das Faixas de Priorização:")
    for faixa, qtd in metadados["distribuicao_faixas"].items():
        pct = (qtd / len(df_resultado)) * 100
        print(f"     * Faixa {faixa:<6}: {qtd:>5} devedores ({pct:>5.1f}%)")

    # 3. Priorização por Heap Máximo
    print("\n🌲 Priorização da Fila de Cobrança com Heap Máximo O(log n):")
    fila_heap = pipeline.priorizar_fila_cobranca(df_resultado)
    print(f"   - Total de débitos enfileirados: {len(fila_heap)}")
    print(f"   - Top {min(args.amostra, len(fila_heap))} débitos prioritários para cobrança imediata:")
    for item in fila_heap[:args.amostra]:
        print(f"     #{item['posicao']:<2} | Score: {item['score_recuperabilidade']:>4.1f} | Dívida: {item['id_divida']:<18} | Valor: R$ {item['valor_total_divida']:>10,.2f}")

    print("\n" + "=" * 80)
    print("Para iniciar o painel interativo web, execute: python src/main.py --dashboard")
    print("=" * 80)


if __name__ == "__main__":
    main()
