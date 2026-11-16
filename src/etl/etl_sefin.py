from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path

import pandas as pd

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.etl.enriquecimento_ibge import enriquecer_com_ibge


RAIZ = Path(__file__).resolve().parents[2]
BRUTO = RAIZ / "data" / "bruto"
LIMPO = RAIZ / "data" / "limpo"
PRONTO = RAIZ / "data" / "pronto"
LOGS = RAIZ / "logs"

IBGE = BRUTO / "ibge_setores_palmas.csv"

for diretorio in (LIMPO, PRONTO, LOGS):
    diretorio.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(
            LOGS / "etl_execucao.log",
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)

log = logging.getLogger("etl_sefin")

ALIASES = {
    "cpf_cnpj": ["cpf_cnpj", "cpf", "cnpj"],
    "nome": ["nome", "contribuinte"],
    "inscricao_imobiliaria": [
        "inscricao_imobiliaria", "inscricao_iptu"
    ],
    "logradouro": ["logradouro", "endereco", "endereço"],
    "bairro": ["bairro"],
    "setor": ["setor", "setor_urbano"],
    "area_edificada_m2": ["area_edificada_m2", "area_edificada"],
    "tipo_tributo": ["tipo_tributo", "tributo"],
    "exercicio": ["exercicio", "ano_exercicio"],
    "valor_consolidado": [
        "valor_consolidado", "valor_debito", "valor_divida"
    ],
    "score_recuperabilidade": ["score_recuperabilidade"],
    "status_cobranca": ["status_cobranca"],
    "data_vencimento": ["data_vencimento", "vencimento"],
    "data_referencia": [
        "data_referencia", "data_ocorrencia", "data",
        "receita_data_ocorrencia",
    ],
    "mes": ["mes", "mês"],
    "valor": [
        "valor", "receita_valor", "valor_arrecado_mes",
        "valor_arrecado_periodo", "valor_mov",
        "valor_pagamento", "valor_empenho",
    ],
}


def numero(serie: pd.Series) -> pd.Series:
    texto = serie.astype("string").str.strip()
    texto = texto.str.replace(r"R\$\s*", "", regex=True)
    texto = texto.str.replace(r"\s+", "", regex=True)

    brasileiro = texto.str.contains(",", na=False)
    texto.loc[brasileiro] = (
        texto.loc[brasileiro]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )

    return pd.to_numeric(texto, errors="coerce")


def extrair() -> tuple[pd.DataFrame, int]:
    arquivos = sorted(
        p for p in BRUTO.iterdir()
        if p.is_file()
        and p.suffix.lower() in {".csv", ".json"}
        and p.name != IBGE.name
    )

    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum arquivo CSV/JSON encontrado em {BRUTO}"
        )

    tabelas = []
    total = 0

    for arquivo in arquivos:
        if arquivo.suffix.lower() == ".csv":
            original = pd.read_csv(
                arquivo,
                sep=None,
                engine="python",
                encoding="utf-8-sig",
                dtype="string",
                on_bad_lines="warn",
            )
        else:
            original = pd.read_json(arquivo, encoding="utf-8")

        if original.empty:
            log.warning("Arquivo vazio: %s", arquivo.name)
            continue

        total += len(original)
        original.columns = [
            str(c).strip().lower() for c in original.columns
        ]

        tabela = pd.DataFrame(index=original.index)
        tabela["fonte"] = arquivo.name

        for destino, aliases in ALIASES.items():
            coluna = next(
                (a for a in aliases if a in original.columns),
                None,
            )
            tabela[destino] = (
                original[coluna] if coluna else pd.NA
            )

        tabelas.append(tabela)
        log.info("Extraído %s: %s linhas", arquivo.name, len(original))

    if not tabelas:
        raise ValueError("Os arquivos não contêm registros aproveitáveis.")

    return pd.concat(tabelas, ignore_index=True), total


def transformar(
    base: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    dados = base.copy()
    inconsistencias = 0

    for coluna in [
        "cpf_cnpj", "nome", "inscricao_imobiliaria",
        "logradouro", "bairro", "setor", "tipo_tributo",
        "status_cobranca",
    ]:
        dados[coluna] = (
            dados[coluna].astype("string").str.strip().replace("", pd.NA)
        )

    for coluna in ["data_vencimento", "data_referencia"]:
        original = dados[coluna]
        convertida = pd.to_datetime(
            original, errors="coerce", dayfirst=True
        )
        inconsistencias += int(
            (original.notna() & original.ne("") & convertida.isna()).sum()
        )
        dados[coluna] = convertida

    for coluna in [
        "valor", "valor_consolidado", "score_recuperabilidade",
        "area_edificada_m2",
    ]:
        original = dados[coluna]
        convertido = numero(original)
        inconsistencias += int(
            (original.notna() & original.ne("") & convertido.isna()).sum()
        )
        dados[coluna] = convertido

    for coluna in ["exercicio", "mes"]:
        dados[coluna] = pd.to_numeric(
            dados[coluna], errors="coerce"
        ).astype("Int64")

    antes = len(dados)
    dados = dados.drop_duplicates().copy()
    inconsistencias += antes - len(dados)

    dados["valor_analise"] = dados["valor_consolidado"].combine_first(
        dados["valor"]
    )

    return dados, inconsistencias


def engenharia_atributos(base: pd.DataFrame) -> pd.DataFrame:
    dados = base.copy()
    hoje = pd.Timestamp(date.today())

    dados["tempo_inadimplencia_dias"] = (
        hoje - dados["data_vencimento"]
    ).dt.days.clip(lower=0).astype("Int64")

    valor = dados["valor_analise"]

    dados["faixa_valor"] = "Não informado"
    dados.loc[valor.notna() & valor.lt(1000), "faixa_valor"] = (
        "Pequeno Débito"
    )
    dados.loc[valor.ge(1000) & valor.le(10000), "faixa_valor"] = "Médio"
    dados.loc[valor.gt(10000), "faixa_valor"] = "Grande"

    mes_data = dados["data_referencia"].dt.month
    mes = dados["mes"].combine_first(mes_data).astype("Int64")
    dados["sazonalidade_mes"] = mes

    trimestre = ((mes - 1) // 3 + 1).astype("Int64")
    dados["sazonalidade_trimestre"] = (
        "Q" + trimestre.astype("string")
    ).where(mes.between(1, 12), pd.NA)

    return dados


def carregar_postgres(base: pd.DataFrame) -> int:
    # Não inferimos contribuintes, imóveis ou dívidas a partir
    # de despesas e receitas genéricas.
    campos = {
        "cpf_cnpj", "nome", "inscricao_imobiliaria",
        "logradouro", "bairro", "setor", "tipo_tributo",
        "exercicio", "valor_consolidado",
    }

    if not campos.issubset(base.columns):
        log.warning("Carga cancelada: faltam campos relacionais.")
        return 0

    url = os.getenv("DATABASE_URL")
    if not url and not os.getenv("PGHOST"):
        log.warning(
            "Carga não executada: configure DATABASE_URL ou PGHOST, "
            "PGDATABASE, PGUSER e PGPASSWORD."
        )
        return 0

    try:
        import psycopg2
    except ImportError as exc:
        raise RuntimeError(
            "Instale psycopg2-binary para habilitar a carga."
        ) from exc

    validos = base.dropna(subset=list(campos)).copy()
    if validos.empty:
        log.warning(
            "Carga não executada: não há registros tributários "
            "completos nas fontes atuais."
        )
        return 0

    parametros = (
        {"dsn": url}
        if url
        else {
            "host": os.environ["PGHOST"],
            "dbname": os.environ["PGDATABASE"],
            "user": os.environ["PGUSER"],
            "password": os.environ["PGPASSWORD"],
            "port": os.getenv("PGPORT", "5432"),
        }
    )

    conexao = psycopg2.connect(**parametros)
    inseridos = 0

    try:
        with conexao:
            with conexao.cursor() as cursor:
                for _, linha in validos.iterrows():
                    tipo = str(linha["tipo_tributo"]).strip().upper()

                    if tipo not in {"IPTU", "ISS", "ITBI", "TAXAS"}:
                        continue

                    valor = float(linha["valor_consolidado"])
                    if valor < 0:
                        continue

                    cursor.execute(
                        """
                        INSERT INTO contribuinte
                            (cpf_cnpj, nome, isencao_iptu_social)
                        VALUES (%s, %s, FALSE)
                        ON CONFLICT (cpf_cnpj) DO UPDATE
                        SET nome = EXCLUDED.nome
                        RETURNING id_contribuinte
                        """,
                        (str(linha["cpf_cnpj"]), str(linha["nome"])),
                    )
                    id_contribuinte = cursor.fetchone()[0]

                    cursor.execute(
                        """
                        INSERT INTO imovel (
                            inscricao_imobiliaria, id_contribuinte,
                            logradouro, bairro, setor, area_edificada_m2
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (inscricao_imobiliaria) DO UPDATE SET
                            id_contribuinte = EXCLUDED.id_contribuinte,
                            logradouro = EXCLUDED.logradouro,
                            bairro = EXCLUDED.bairro,
                            setor = EXCLUDED.setor,
                            area_edificada_m2 = EXCLUDED.area_edificada_m2
                        """,
                        (
                            str(linha["inscricao_imobiliaria"]),
                            id_contribuinte,
                            str(linha["logradouro"]),
                            str(linha["bairro"]),
                            str(linha["setor"]),
                            (
                                float(linha["area_edificada_m2"])
                                if pd.notna(linha["area_edificada_m2"])
                                else None
                            ),
                        ),
                    )

                    cursor.execute(
                        """
                        SELECT id_divida FROM divida_ativa
                        WHERE inscricao_imobiliaria = %s
                          AND tipo_tributo = %s
                          AND exercicio = %s
                          AND valor_consolidado = %s
                        LIMIT 1
                        """,
                        (
                            str(linha["inscricao_imobiliaria"]),
                            tipo,
                            int(linha["exercicio"]),
                            valor,
                        ),
                    )

                    if cursor.fetchone():
                        continue

                    score = linha["score_recuperabilidade"]
                    score = (
                        float(score)
                        if pd.notna(score) and 0 <= float(score) <= 100
                        else None
                    )

                    status = linha["status_cobranca"]
                    if status not in {
                        "Em Aberto", "Ajuizado", "Parcelado", "Quitado"
                    }:
                        status = "Em Aberto"

                    cursor.execute(
                        """
                        INSERT INTO divida_ativa (
                            inscricao_imobiliaria, tipo_tributo, exercicio,
                            valor_consolidado, score_recuperabilidade,
                            status_cobranca
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            str(linha["inscricao_imobiliaria"]),
                            tipo,
                            int(linha["exercicio"]),
                            valor,
                            score,
                            status,
                        ),
                    )
                    inseridos += 1

        log.info("Novas dívidas inseridas: %s", inseridos)
        return inseridos

    except Exception:
        log.exception("Erro na carga; transação revertida.")
        raise
    finally:
        conexao.close()


def executar() -> None:
    bruta, total_lido = extrair()
    log.info("Total de linhas lidas: %s", total_lido)

    limpa, inconsistencias = transformar(bruta)
    limpa.to_csv(
        LIMPO / "base_limpa.csv",
        sep=";",
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )

    pronta = enriquecer_com_ibge(limpa, IBGE)
    pronta = engenharia_atributos(pronta)

    pronta.to_csv(
        PRONTO / "base_pronta.csv",
        sep=";",
        index=False,
        encoding="utf-8-sig",
        date_format="%Y-%m-%d",
    )

    log.info("Linhas tratadas: %s", len(limpa))
    log.info("Inconsistências corrigidas/removidas: %s", inconsistencias)
    log.info(
        "Indicadores de renda IBGE preenchidos: %s",
        int(pronta["renda_media_domiciliar"].notna().sum()),
    )

    inseridos = carregar_postgres(pronta)
    log.info("Total inserido no banco: %s", inseridos)
    log.info("ETL finalizado.")


if __name__ == "__main__":
    try:
        executar()
    except Exception:
        log.exception("Falha na execução do ETL.")
        raise
