"""
Gerador de Dados Sintéticos e Anonimizados - Dívida Ativa SEFIN Palmas-TO
Projeto Integrador Eixo II - BIINAR / UFT - Sprint 4
Conformidade Ética e LGPD: minimização de dados, identificadores mascarados,
sem exposição de dados pessoais reais.
"""

import numpy as np
import pandas as pd
import random
import os

def generate_sefin_data(n_samples=2500, random_state=42):
    np.random.seed(random_state)
    random.seed(random_state)

    # Regiões e Setores de Palmas - TO com coordenadas representativas
    locais_palmas = [
        {"regiao": "Plano Diretor Sul", "bairro": "Plano Diretor Sul (104 Sul)", "lat": -10.1885, "lon": -48.3325, "renda_peso": [0.05, 0.20, 0.45, 0.30]},
        {"regiao": "Plano Diretor Sul", "bairro": "Plano Diretor Sul (208 Sul)", "lat": -10.2012, "lon": -48.3280, "renda_peso": [0.05, 0.25, 0.45, 0.25]},
        {"regiao": "Plano Diretor Sul", "bairro": "Plano Diretor Sul (704 Sul)", "lat": -10.2250, "lon": -48.3310, "renda_peso": [0.10, 0.35, 0.40, 0.15]},
        {"regiao": "Plano Diretor Sul", "bairro": "Plano Diretor Sul (1104 Sul)", "lat": -10.2450, "lon": -48.3295, "renda_peso": [0.15, 0.40, 0.35, 0.10]},
        {"regiao": "Plano Diretor Norte", "bairro": "Plano Diretor Norte (104 Norte)", "lat": -10.1750, "lon": -48.3315, "renda_peso": [0.10, 0.35, 0.40, 0.15]},
        {"regiao": "Plano Diretor Norte", "bairro": "Plano Diretor Norte (303 Norte)", "lat": -10.1655, "lon": -48.3240, "renda_peso": [0.15, 0.40, 0.35, 0.10]},
        {"regiao": "Plano Diretor Norte", "bairro": "Plano Diretor Norte (603 Norte)", "lat": -10.1540, "lon": -48.3200, "renda_peso": [0.20, 0.45, 0.25, 0.10]},
        {"regiao": "Jardins Aureny", "bairro": "Jardim Aureny I", "lat": -10.2680, "lon": -48.3180, "renda_peso": [0.35, 0.45, 0.17, 0.03]},
        {"regiao": "Jardins Aureny", "bairro": "Jardim Aureny III", "lat": -10.2820, "lon": -48.3110, "renda_peso": [0.40, 0.45, 0.13, 0.02]},
        {"regiao": "Jardins Aureny", "bairro": "Jardim Aureny IV", "lat": -10.2910, "lon": -48.3050, "renda_peso": [0.45, 0.40, 0.13, 0.02]},
        {"regiao": "Região Sul (Taquaralto)", "bairro": "Taquaralto Centro", "lat": -10.3180, "lon": -48.3090, "renda_peso": [0.35, 0.45, 0.17, 0.03]},
        {"regiao": "Região Sul (Taquaralto)", "bairro": "Belo Horizonte / Taquaralto", "lat": -10.3290, "lon": -48.3020, "renda_peso": [0.45, 0.40, 0.13, 0.02]},
        {"regiao": "Setor Taquari", "bairro": "Jardim Taquari", "lat": -10.3020, "lon": -48.2720, "renda_peso": [0.55, 0.35, 0.09, 0.01]},
        {"regiao": "Distrito de Taquaruçu", "bairro": "Taquaruçu", "lat": -10.3200, "lon": -48.1550, "renda_peso": [0.30, 0.45, 0.20, 0.05]}
    ]

    tributos = ["IPTU", "ISSQN", "ITBI", "Taxas de Licenciamento", "Multas de Obras/Posturas"]
    faixas_renda = ["Até 2 SM", "2 a 5 SM", "5 a 10 SM", "Acima de 10 SM"]
    tipos_pessoa = ["Pessoa Física (PF)", "Pessoa Jurídica (PJ)"]

    nomes_ficticios = [
        "A. R. Silva", "M. F. Oliveira", "C. E. Santos", "J. P. Almeida", 
        "F. H. Costa", "L. M. Souza", "R. B. Pereira", "G. N. Rodrigues",
        "Palmas Logística ME", "Norte Engenharia EIRELI", "Cerrado Comércio de Peças LTDA",
        "Tocantins Distribuidora MEI", "Araguaia Serviços Médicos", "Girassol Hotelaria S/A"
    ]

    data = []
    for i in range(1, n_samples + 1):
        # Seleciona localização
        loc = random.choice(locais_palmas)
        # Ruído nas coordenadas para dispersão realista no mapa
        lat_jitter = np.random.normal(0, 0.0035)
        lon_jitter = np.random.normal(0, 0.0035)

        t_pessoa = np.random.choice(tipos_pessoa, p=[0.72, 0.28])
        tributo = np.random.choice(tributos, p=[0.48, 0.27, 0.10, 0.10, 0.05])
        faixa_renda = np.random.choice(faixas_renda, p=loc["renda_peso"])

        # Identificadores anonimizados
        doc_num = f"{random.randint(100, 999)}.{random.randint(100, 999)}.{random.randint(100, 999)}-{random.randint(10, 99)}" if t_pessoa.startswith("Pessoa F") else f"{random.randint(10, 99)}.{random.randint(100, 999)}.{random.randint(100, 999)}/0001-{random.randint(10, 99)}"
        doc_mascarado = f"***.{doc_num.split('.')[1]}.***-**" if t_pessoa.startswith("Pessoa F") else f"**.{doc_num.split('.')[1]}.***/0001-**"

        nome_base = random.choice(nomes_ficticios)
        contribuinte = f"Contribuinte {nome_base} ({'PF' if 'Física' in t_pessoa else 'PJ'})"
        id_devedor = f"SEFIN-PMW-{100000 + i}"
        cda_num = f"202{random.randint(0,4)}/CDA-{random.randint(10000, 99999)}"

        # Exercício fiscal e tempo em dívida ativa (split temporal)
        ano_inscricao = np.random.choice([2019, 2020, 2021, 2022, 2023, 2024], p=[0.10, 0.12, 0.18, 0.25, 0.20, 0.15])
        meses_em_divida = (2026 - ano_inscricao) * 12 + random.randint(1, 11)

        # Valores financeiros correlacionados com o tributo e tipo de pessoa
        if tributo == "IPTU":
            valor_base = np.random.exponential(scale=3500) + 400
        elif tributo == "ISSQN":
            valor_base = np.random.exponential(scale=12000) + 1200
        elif tributo == "ITBI":
            valor_base = np.random.exponential(scale=8500) + 1000
        else:
            valor_base = np.random.exponential(scale=2200) + 300

        if t_pessoa.startswith("Pessoa J"):
            valor_base *= np.random.uniform(1.8, 3.5)

        valor_principal = round(valor_base, 2)
        # Juros e multas proporcionais ao tempo de atraso
        taxa_juros = 0.01 * (meses_em_divida * 0.8)
        juros_multas = round(valor_principal * min(taxa_juros, 0.65), 2)
        valor_total = round(valor_principal + juros_multas, 2)

        # Histórico de cobrança
        qtd_debitos = np.random.choice([1, 2, 3, 4, 5, 6, 8, 12], p=[0.35, 0.25, 0.15, 0.10, 0.07, 0.04, 0.03, 0.01])
        historico_parcelamentos = np.random.choice([0, 1, 2, 3], p=[0.50, 0.30, 0.15, 0.05])
        execucao_ajuizada = np.random.choice(["Sim", "Não"], p=[0.22, 0.78] if meses_em_divida < 36 else [0.55, 0.45])
        possui_bens_penhoraveis = np.random.choice(["Sim", "Não"], p=[0.45, 0.55] if faixa_renda in ["5 a 10 SM", "Acima de 10 SM"] else [0.18, 0.82])
        contato_atualizado = np.random.choice(["Sim", "Não"], p=[0.70, 0.30])

        # Modelagem de Score de Recuperabilidade (Lógica baseada em evidência empírica fiscal)
        # Fatores positivos: menos tempo, menor valor relativo, contato atualizado, bens penhoráveis, renda mais alta
        # Fatores negativos: tempo > 4 anos, ajuizado sem sucesso, múltiplos débitos sem parcelamento
        base_score = 65.0
        
        # Efeito tempo
        base_score -= (meses_em_divida / 12) * 4.5
        
        # Efeito valor
        if valor_total < 3000:
            base_score += 12.0
        elif valor_total > 50000:
            base_score -= 10.0
            
        # Efeito contato e garantias
        if contato_atualizado == "Sim":
            base_score += 10.0
        if possui_bens_penhoraveis == "Sim":
            base_score += 12.0
        if historico_parcelamentos > 0:
            base_score += 8.0
        if execucao_ajuizada == "Sim":
            base_score -= 6.0
            
        # Efeito renda/perfil
        if faixa_renda == "Acima de 10 SM":
            base_score += 8.0
        elif faixa_renda == "Até 2 SM":
            base_score -= 8.0

        # Ruído estocástico
        base_score += np.random.normal(0, 7)
        score_recuperabilidade = float(np.clip(base_score, 5.0, 98.5))
        probabilidade_pagamento = round(score_recuperabilidade / 100.0, 3)

        # Categorização por Faixas
        if score_recuperabilidade >= 68.0:
            faixa = "Alta"
            canal_sugerido = "Cobrança Digital (WhatsApp / E-mail / DDA)"
        elif score_recuperabilidade >= 42.0:
            faixa = "Média"
            canal_sugerido = "Protesto Notarial / Notificação Postal"
        else:
            faixa = "Baixa"
            canal_sugerido = "Execução Fiscal / Investigação Patrimonial"

        # Split temporal (conforme metodologia do projeto integrador Sprint 4)
        split_set = "Treino (2019-2022)" if ano_inscricao <= 2022 else ("Validação (2023)" if ano_inscricao == 2023 else "Teste (2024)")

        data.append({
            "id_devedor": id_devedor,
            "contribuinte": contribuinte,
            "documento_mascarado": doc_mascarado,
            "tipo_pessoa": t_pessoa,
            "numero_cda": cda_num,
            "tributo": tributo,
            "ano_inscricao": ano_inscricao,
            "tempo_inscricao_meses": meses_em_divida,
            "valor_principal": valor_principal,
            "juros_multas": juros_multas,
            "valor_total_divida": valor_total,
            "quantidade_debitos": qtd_debitos,
            "historico_parcelamentos": historico_parcelamentos,
            "execucao_ajuizada": execucao_ajuizada,
            "possui_bens": possui_bens_penhoraveis,
            "contato_atualizado": contato_atualizado,
            "faixa_renda": faixa_renda,
            "regiao": loc["regiao"],
            "bairro_setor": loc["bairro"],
            "latitude": round(loc["lat"] + lat_jitter, 5),
            "longitude": round(loc["lon"] + lon_jitter, 5),
            "score_recuperabilidade": round(score_recuperabilidade, 1),
            "probabilidade_pagamento": probabilidade_pagamento,
            "faixa_recuperabilidade": faixa,
            "canal_recomendado": canal_sugerido,
            "split_temporal": split_set
        })

    df = pd.DataFrame(data)
    return df

if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(out_dir, exist_ok=True)
    df = generate_sefin_data(n_samples=2500)
    out_file = os.path.join(out_dir, "divida_ativa_palmas.csv")
    df.to_csv(out_file, index=False, encoding="utf-8")
    print(f"Dataset sintético gerado com sucesso em: {out_file} com {len(df)} registros.")
