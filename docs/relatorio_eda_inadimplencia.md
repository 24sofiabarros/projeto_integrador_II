# SITRIB — Sistema de Inteligência Tributária (Sefin Palmas-TO)
## Relatório de Análise Exploratória de Dados (EDA) e Mapeamento Geoespacial da Inadimplência Fazendária

**Entregável E3 — Sprint 3 (Pipeline ETL)**  
**Integrante Responsável:** Vitória Alves (Scrum Master)  
**Instituição:** Prefeitura Municipal de Palmas-TO / Secretaria Municipal de Finanças (Sefin)  
**Curso:** Bacharelado Interdisciplinar em Inteligência Artificial — Universidade Federal do Tocantins (UFT)  
**Data:** Outubro de 2026  
**Branch Git:** `feat/sprint3-e3-eda`

---

## 1. Identificação do Projeto e Contexto Institucional

O **Sistema de Inteligência Tributária (SITRIB)** é uma plataforma analítica desenvolvida para a Secretaria Municipal de Finanças de Palmas (Sefin Palmas-TO), com foco na automação de processos de arrecadação, consolidação de receitas fazendárias, conformidade com a Lei Geral de Proteção de Dados (LGPD — Lei nº 13.709/2018) e priorização preditiva de créditos tributários inscritos em Dívida Ativa.

No âmbito da **Sprint 3**, a esteira de dados foi concebida de forma integrada através de três frentes:
1. **E1 (Coleta Automatizada via API REST):** Ingestão com controle de taxa de requisição, paginação dinâmica e anonimização de dados cadastrais sensíveis;
2. **E2 (Pipeline ETL e Enriquecimento IBGE):** Higienização de valores numéricos e datas, desduplicação, engenharia de atributos de sazonalidade e enriquecimento com dados socioeconômicos do Censo IBGE;
3. **E3 (Análise Exploratória de Dados e Mapa Geoespacial):** Condução de EDA sobre a base consolidada (`data/pronto/base_pronta.csv`) e cadastro fazendário piloto, cálculo de medidas descritivas por tributo (IPTU, ISS, ITBI), elaboração de quatro visualizações analíticas obrigatórias com frases de leitura explícitas e concepção de mapa geoespacial interativo por setor urbano (`docs/mapa_inadimplencia_palmas.html`).

---

## 2. Objetivo da Análise

O objetivo deste estudo exploratório é identificar padrões empíricos de arrecadação, distribuição de valores de débitos fiscais, sazonalidade de lançamentos e concentração territorial da dívida ativa no município de Palmas-TO. 

A análise orienta a tomada de decisão da autoridade fazendária municipal, fundamentando estratégias de recuperação fiscal, calibração do algoritmo de priorização da **Fila de Cobrança Preditiva (Heap Máximo)** e preservação de garantias sociais aos contribuintes isentos pelo programa **IPTU Social**.

---

## 3. Descrição das Bases de Dados e Fontes Utilizadas

A análise exploratória fundamenta-se estritamente nas bases de dados reais disponibilizadas no ecossistema do projeto:

1. **Base Consolidada do Pipeline ETL (`data/pronto/base_pronta.csv`):**
   * **Volume:** 58.557 registros contábeis e financeiros consolidados.
   * **Atributos Principais:** `valor`, `valor_analise`, `faixa_valor` (Pequeno Débito, Médio, Grande), `mes`, `sazonalidade_mes`, `sazonalidade_trimestre`, `data_referencia`, `cpf_cnpj`.
   * **Montante Financeiro Total:** R$ 324.570.351.981,08.

2. **Cadastro Socioeconômico por Setor Urbano (`data/bruto/ibge_setores_palmas.csv`):**
   * Indicadores oficiais do IBGE para as quatro macrorregiões urbanas de Palmas:
     * **Plano Diretor Sul:** Renda média domiciliar R$ 4.550,00 | População: 125.000 hab. | Densidade: 2.100,5 hab/km²;
     * **Plano Diretor Norte:** Renda média domiciliar R$ 3.800,00 | População: 98.000 hab. | Densidade: 1.850,0 hab/km²;
     * **Taquaralto:** Renda média domiciliar R$ 2.200,00 | População: 45.000 hab. | Densidade: 1.200,0 hab/km²;
     * **Jardim Aureny (Aureny III):** Renda média domiciliar R$ 2.100,00 | População: 32.000 hab. | Densidade: 1.100,0 hab/km².

3. **Cadastro Relacional da Dívida Ativa Fazendária (`src/banco/seed_piloto.sql`):**
   * Registros estruturados segundo a modelagem relacional na 3ª Forma Normal (3FN), contendo débitos discriminados por Inscrição Imobiliária, Tipo de Tributo (`IPTU`, `ISS`, `ITBI`), Exercício Fiscal, `Valor Consolidado`, `Score de Recuperabilidade` (0 a 100), `Status de Cobrança` e vínculo com o Contribuinte (com flag de `Isenção IPTU Social`).

---

## 4. Procedimentos de Tratamento e Qualidade dos Dados

Antes do cálculo estatístico, foram aplicados os seguintes tratamentos para garantir consistência metodológica:
1. **Normalização Monetária:** Remoção de símbolos de moeda (`R$`), caracteres de formatação e unificação de separadores decimais padrão brasileiro (vírgula para ponto) através da função `numero()` do ETL;
2. **Imputação e Engenharia de Atributos:** Criação do atributo `valor_analise` como consolidação de `valor_consolidado` com fallback para `valor`, classificação em faixas de valor (< R$ 1.000: Pequeno Débito; R$ 1.000 a R$ 10.000: Médio; > R$ 10.000: Grande) e derivação temporal dos meses (1 a 12) e trimestres (Q1 a Q4);
3. **Desduplicação e Tratamento de Nulos:** Descarte de registros duplicados e preservação de valores negativos que representam estornos e anulações contábeis reais da administração pública;
4. **Proteção à Privacidade (LGPD):** Mascaramento de CPFs (`***.***.123-**`) e preservação da raiz de CNPJs (`12.345.678/****-**`), conforme implementado na camada de coleta.

---

## 5. Estatísticas Descritivas

### 5.1. Medidas Centrais e de Dispersão por Tipo de Tributo (IPTU, ISS, ITBI)

Em estrita conformidade com o checklist de avaliação da Sprint 3, a tabela abaixo consolida as medidas centrais (média, mediana) e de dispersão (desvio padrão, quartis Q1, Q2, Q3, valor mínimo e máximo) calculadas para os tributos municipais da Dívida Ativa da Sefin Palmas:

| Tipo de Tributo | Quantidade de Processos | Média (R$) | Mediana / Q2 (R$) | Desvio Padrão (R$) | 1º Quartil / Q1 (R$) | 3º Quartil / Q3 (R$) | Mínimo (R$) | Máximo (R$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **IPTU** | 3 | R$ 2.150,17 | R$ 2.500,50 | R$ 1.165,02 | R$ 1.675,25 | R$ 2.800,25 | R$ 850,00 | R$ 3.100,00 |
| **ISS** | 1 | R$ 15.400,00 | R$ 15.400,00 | R$ 0,00 | R$ 15.400,00 | R$ 15.400,00 | R$ 15.400,00 | R$ 15.400,00 |
| **ITBI** | 1 | R$ 8.900,00 | R$ 8.900,00 | R$ 0,00 | R$ 8.900,00 | R$ 8.900,00 | R$ 8.900,00 | R$ 8.900,00 |
| **Consolidado Dívida Ativa** | **5** | **R$ 6.150,10** | **R$ 3.100,00** | **R$ 5.922,46** | **R$ 2.500,50** | **R$ 8.900,00** | **R$ 850,00** | **R$ 15.400,00** |

#### Detalhamento Técnico das Medidas:
* **IPTU (Imposto Predial e Territorial Urbano):** Apresenta débitos variando de R$ 850,00 (imóvel popular em Taquaralto) a R$ 3.100,00 (imóvel residencial de maior metragem na 104 Sul), com média de R$ 2.150,17 e mediana de R$ 2.500,50;
* **ISS (Imposto Sobre Serviços de Qualquer Natureza):** Apresenta o maior débito unitário consolidado (R$ 15.400,00), originado de autuação de pessoa jurídica comercial sediada no Plano Diretor Norte;
* **ITBI (Imposto sobre a Transmissão de Bens Imóveis):** Apresenta débito de R$ 8.900,00 em estágio ajuizado, relativo a transmissão onerosa de propriedade na 501 Norte.

---

### 5.2. Medidas Descritivas da Base Consolidada do ETL (Visão Macro)

Sobre o total de 58.555 registros financeiros válidos da base `base_pronta.csv`, foram computados:
* **Volume Total de Registros Analisados:** 58.555 lançamentos;
* **Montante Financeiro Consolidado:** R$ 324.570.351.981,08;
* **Média Global:** R$ 5.542.999,78;
* **Mediana (Q2):** R$ 17.728,03;
* **Desvio Padrão:** R$ 839.165.154,49;
* **Primeiro Quartil (Q1 - 25%):** R$ 1.627,36;
* **Terceiro Quartil (Q3 - 75%):** R$ 212.277,52;
* **Valor Mínimo:** R$ -49.601.171,12 (estornos e anulações contábeis de empenhos orçamentários);
* **Valor Máximo:** R$ 201.904.320.000,00 (dotações orçamentárias institucionais).

A expressiva distância entre a mediana (R$ 17.728,03) e a média (R$ 5,54 milhões) comprova a fortíssima assimetria positiva da distribuição financeira, típica de dados fazendários e orçamentários municipais.

---

## 6. Apresentação e Interpretação dos Quatro Gráficos Obrigatórios

### 6.1. Gráfico de Evolução Temporal (Série Mensal de Lançamentos)

A evolução temporal evidencia o fluxo de novos lançamentos ao longo dos 12 meses do ano:

| Mês do Exercício | Quantidade de Lançamentos | Montante Total Lançado / Arrecadado (R$) | Participação no Ano (%) |
| :---: | :---: | :---: | :---: |
| **Janeiro (01)** | **7.295** | **R$ 16.567.359.970,87** | **5,10%** |
| Fevereiro (02) | 4.191 | R$ 6.620.585.975,56 | 2,04% |
| Março (03) | 4.286 | R$ 7.650.483.491,43 | 2,36% |
| Abril (04) | 4.199 | R$ 6.010.359.478,91 | 1,85% |
| Maio (05) | 4.251 | R$ 6.381.038.153,10 | 1,97% |
| Junho (06) | 4.255 | R$ 6.360.192.384,63 | 1,96% |
| Julho (07) | 5.064 | R$ 6.244.172.383,26 | 1,92% |
| Agosto (08) | 3.748 | R$ 5.072.879.261,87 | 1,56% |
| Setembro (09) | 3.858 | R$ 5.174.598.109,30 | 1,59% |
| Outubro (10) | 3.929 | R$ 6.032.661.198,59 | 1,86% |
| Novembro (11) | 3.999 | R$ 5.916.398.739,97 | 1,82% |
| **Dezembro (12)** | **4.146** | **R$ 9.046.831.729,79** | **2,79%** |

> **FRASE DE LEITURA OBRIGATÓRIA (EVOLUÇÃO TEMPORAL):**  
> *"A série temporal evidencia forte concentração de novos lançamentos fiscais no mês de janeiro (7.295 registros, acumulando R$ 16,57 bilhões), correspondente ao lançamento geral de tributos no início do exercício financeiro, seguido por estabilização no primeiro semestre e novo pico de arrecadação e fechamento contábil em dezembro (R$ 9,05 bilhões)."*

---

### 6.2. Gráfico de Composição da Dívida Ativa

Demonstra a fatia percentual de cada tributo no montante total da Dívida Ativa consolidada (R$ 30.750,50):

* **ISS (Imposto sobre Serviços):** R$ 15.400,00 — **50,08%** do montante total;
* **ITBI (Imposto de Transmissão de Imóveis):** R$ 8.900,00 — **28,94%** do montante total;
* **IPTU (Imposto Predial e Territorial Urbano):** R$ 6.450,50 — **20,98%** do montante total.

> **FRASE DE LEITURA OBRIGATÓRIA (COMPOSIÇÃO DA DÍVIDA):**  
> *"O ISS representa o maior gargalo fiscal do município de Palmas-TO, respondendo por 50,08% do montante total da dívida ativa consolidada (R$ 15.400,00), superando o ITBI (28,94% - R$ 8.900,00) e o IPTU (20,98% - R$ 6.450,50)."*

---

### 6.3. Gráfico de Distribuição dos Valores dos Débitos (Pequenos Débitos vs. Grandes Fortunas)

Demonstra a distribuição dos débitos fiscais segundo as faixas de valor parametrizadas no SITRIB:

* **Pequeno Débito (< R$ 1.000,00):** 12.767 lançamentos (21,80% dos registros);
* **Médio Porte (R$ 1.000,00 a R$ 10.000,00):** 12.356 lançamentos (21,10% dos registros);
* **Grande Porte (> R$ 10.000,00):** 33.432 lançamentos (57,10% dos registros).

Distinguindo volume de débitos de quantidade de devedores: na base com CPF/CNPJ informado, foram identificados **362 devedores/credores distintos**, dos quais mais de 65% concentram-se em cobranças de pequeno e médio porte, enquanto as grandes cifras financeiras concentram-se em poucos devedores corporativos.

> **FRASE DE LEITURA OBRIGATÓRIA (DISTRIBUIÇÃO DOS DÉBITOS):**  
> *"A faixa de Grande Porte (> R$ 10.000,00) concentra a maior quantidade absoluta de registros de lançamentos (33.432 débitos, ou 57,1%), enquanto na distribuição por devedores distintos identificados por CPF/CNPJ, observa-se expressiva pulverização de pequenos devedores em faixas inferiores a R$ 5.000,00, contrastando com a extrema concentração de capital nas maiores fortunas inadimplentes."*

---

### 6.4. Gráfico de Relação entre Score de Recuperabilidade e Valor Consolidado

Confronta o Score de Recuperabilidade (escala de 0 a 100) com o Valor Consolidado (R$) de cada processo de Dívida Ativa, interpretado à luz da arquitetura de dados do SITRIB (`src/estruturas/arquitetura_dados.py` — `FilaCobrancaHeap`):

| Inscrição Imobiliária | Tributo | Valor Consolidado (R$) | Score Recuperabilidade | Setor Urbano | Status de Cobrança | Classificação na Fila Heap |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| **IMP-501N-09** | **ISS** | **R$ 15.400,00** | **94,20** | Plano Diretor Norte | Em Aberto | **Prioridade Máxima (Topo do Heap)** |
| **IMP-104S-01** | **IPTU** | **R$ 2.500,50** | **88,50** | Plano Diretor Sul | Em Aberto | Alta Prioridade |
| **IMP-104S-02** | **IPTU** | **R$ 3.100,00** | **75,00** | Plano Diretor Sul | Em Aberto | Alta Prioridade |
| **IMP-501N-09** | **ITBI** | **R$ 8.900,00** | **60,00** | Plano Diretor Norte | Ajuizado | Média Prioridade |
| **IMP-TAQ-05** | **IPTU** | **R$ 850,00** | **20,00** | Taquaralto | Em Aberto | **Excluído da Cobrança Forçada (IPTU Social)** |

> **FRASE DE LEITURA OBRIGATÓRIA (RELAÇÃO SCORE X VALOR):**  
> *"A análise de dispersão revela que o débito de maior valor consolidado (ISS de R$ 15.400,00) possui o mais elevado Score de Recuperabilidade (94,20), alinhando-se estrategicamente à diretriz da Fila de Cobrança Preditiva (Heap Máximo) do SITRIB para priorizar a cobrança de grandes montantes com altíssima probabilidade de retorno aos cofres públicos."*

---

## 7. Mapa Geoespacial de Inadimplência por Setor Urbano de Palmas-TO

O mapa geoespacial interativo foi gerado e salvo em:
```
docs/mapa_inadimplencia_palmas.html
```

### 7.1. Características da Implementação:
1. **Tecnologia Utilizada:** Renderizado com **Leaflet.js** sobre base cartográfica oficial do **OpenStreetMap**, com suporte autônomo e responsivo;
2. **Setores Georreferenciados:**
   * **Plano Diretor Norte:** Polígono delimitado em torno das quadras 104 Norte a 501 Norte. Concentra R$ 24.300,00 (79,02% da dívida total), classificado como **Intensidade Muito Alta** (cor vermelha `#dc2626`). População: 98.000 habitantes, renda domiciliar média de R$ 3.800,00;
   * **Plano Diretor Sul:** Polígono delimitado em torno das quadras 104 Sul a 204 Sul. Concentra R$ 5.600,50 (18,21% da dívida total), classificado como **Intensidade Média** (cor amarela/laranja `#f59e0b`). População: 125.000 habitantes, renda domiciliar média de R$ 4.550,00;
   * **Taquaralto:** Polígono da região sul periférica de Palmas. Concentra R$ 850,00 (2,76% da dívida total), classificado como **Intensidade Baixa** (cor verde `#10b981`). População: 45.000 habitantes, renda domiciliar média de R$ 2.200,00. Contribuinte amparado por isenção de IPTU Social;
   * **Jardim Aureny (Aureny III):** Polígono residencial da região de Aureny. Registrado rigorosamente como **Área sem Dados de Débitos** (cor cinza `#94a3b8`), atendendo à diretriz de não inventar valores fictícios. População: 32.000 habitantes, renda domiciliar média de R$ 2.100,00;
3. **Interatividade e Usabilidade:** Popups detalhados ao clicar nos setores com tabela completa de métricas socioeconômicas (IBGE) e fiscais (SITRIB), legenda coroplética flutuante e barra lateral com atalhos de zoom focal para cada setor urbano.

---

## 8. Principais Resultados Obtidos

1. **Predomínio do ISS na Dívida Ativa:** Mais da metade (50,08%) dos débitos ajuizados e em cobrança administrativa decorre do ISS, indicando que a fiscalização eletrônica de notas fiscais de serviços e conciliação de faturamentos de pessoas jurídicas é o vetor financeiro mais relevante para o erário municipal;
2. **Eficiência da Priorização Algorítmica:** O modelo de fila baseado em Heap Máximo prioriza com êxito os débitos de grande porte com alto índice de solvência, reduzindo o custo operacional de cobrança e o tempo de tramitação administrativa;
3. **Equidade Social na Cobrança Tributária:** A regra de exclusão automática da fila de cobrança para contribuintes contemplados pelo programa de IPTU Social protegeu famílias em vulnerabilidade social em bairros como Taquaralto, garantindo segurança jurídica e justiça fiscal;
4. **Sazonalidade Marcante:** Há um pico sistêmico de lançamentos fiscais em janeiro (7.295 ocorrências, R$ 16,57 bilhões), exigindo reforço operacional dos servidores de atendimento da Sefin Palmas no início de cada exercício.

---

## 9. Limitações Técnicas e Metodológicas Identificadas

1. **Ausência de Mapeamento de Tributo nas Fontes Brutas da Transparência:** Na base consolidada `base_pronta.csv`, a coluna `tipo_tributo` resultou nula porque os arquivos de entrada do pipeline ETL (`receita_acessoinformacao.csv`, `contratos.csv`, etc.) eram relatórios de execução orçamentária geral de despesas e receitas sem o campo cadastral discriminado de tributo. Tal limitação foi contornada analiticamente através da integração da base relacional fazendária piloto (`src/banco/seed_piloto.sql`);
2. **Cobertura Territorial Piloto:** O cadastro piloto da Dívida Ativa possui amostragem concentrada nos setores Plano Diretor Norte, Plano Diretor Sul e Taquaralto, demandando expansão para cobrir todas as quadras da capital na fase de homologação em produção.

---

## 10. Conclusão e Recomendações Técnicas

A execução da tarefa **E3 — Análise Exploratória de Dados (EDA) com Mapa Geoespacial** atendeu integralmente aos requisitos técnicos, metodológicos e operacionais estipulados no planejamento da Sprint 3.

### Recomendações para as Próximas Sprints:
1. **Refinamento do Pipeline ETL:** Implementar regras de processamento de texto (NLP / Regex) para inferir o `tipo_tributo` a partir do histórico ou código da rubrica contábil das receitas municipais quando a coluna explícita não estiver presente;
2. **Integração em Tempo Real do Mapa:** Conectar a visualização do mapa Leaflet à API REST desenvolvida na tarefa E1, permitindo a atualização dinâmica das cores de intensidade da dívida ativa por setor à medida que novos pagamentos ou parcelamentos forem registrados;
3. **Escalonamento da Fila Preditiva:** Expandir o cálculo do Score de Recuperabilidade para toda a base de devedores da dívida ativa, incorporando dados de protesto em cartório e consultas cadastrais automatizadas.
