from pathlib import Path
import pandas as pd


SETORES_PALMAS = {
    "plano diretor sul": "Plano Diretor Sul",
    "plano diretor norte": "Plano Diretor Norte",
    "taquaralto": "Taquaralto",
    "setor taquaralto": "Taquaralto",
}


def enriquecer_com_ibge(
    base: pd.DataFrame,
    arquivo_ibge: Path | str,
) -> pd.DataFrame:
    dados = base.copy()

    if "setor" not in dados.columns:
        dados["setor"] = pd.NA

    dados["setor"] = (
        dados["setor"].astype("string").str.strip()
    )

    dados["_setor_chave"] = (
        dados["setor"].str.casefold()
    )

    dados["setor"] = dados["_setor_chave"].map(SETORES_PALMAS).fillna(
        dados["setor"]
    )

    caminho = Path(arquivo_ibge)

    if caminho.exists():
        ibge = pd.read_csv(
            caminho,
            sep=None,
            engine="python",
            encoding="utf-8-sig",
        )

        ibge.columns = [
            str(coluna).strip().lower() for coluna in ibge.columns
        ]

        coluna_setor = next(
            (
                c for c in ["setor", "bairro", "nome_setor"]
                if c in ibge.columns
            ),
            None,
        )

        if coluna_setor is None:
            raise ValueError(
                "O arquivo IBGE precisa ter uma coluna "
                "'setor', 'bairro' ou 'nome_setor'."
            )

        ibge["_setor_chave"] = (
            ibge[coluna_setor].astype("string").str.strip().str.casefold()
        )

        ibge = ibge.rename(
            columns={
                "renda_media_domiciliar": "renda_media_domiciliar",
                "populacao": "populacao_setor",
                "populacao_setor": "populacao_setor",
                "densidade_urbana": "densidade_urbana",
            }
        )

        indicadores = [
            c for c in [
                "renda_media_domiciliar",
                "populacao_setor",
                "densidade_urbana",
            ]
            if c in ibge.columns
        ]

        if not indicadores:
            raise ValueError(
                "O arquivo IBGE não contém indicadores reconhecidos."
            )

        ibge = ibge[["_setor_chave", *indicadores]].drop_duplicates(
            subset="_setor_chave"
        )

        dados = dados.merge(
            ibge,
            on="_setor_chave",
            how="left",
        )
        dados = dados.drop(columns="_setor_chave")

    else:
        dados = dados.drop(columns="_setor_chave")

        for coluna in [
            "renda_media_domiciliar",
            "populacao_setor",
            "densidade_urbana",
        ]:
            if coluna not in dados.columns:
                dados[coluna] = pd.NA

    return dados
