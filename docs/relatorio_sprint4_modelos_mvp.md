# UNIVERSIDADE FEDERAL DO TOCANTINS (UFT)
## Bacharelado Interdisciplinar em Inteligência Artificial (BIINAR)
### Eixo II — Projeto Integrador: Sistema de Inteligência Tributária (Sefin Palmas) | Período 2026/2

---

# Relatório Técnico de Entrega — Sprint 4

| Campo | Detalhamento da Entrega |
| :--- | :--- |
| **Projeto** | Sistema de Inteligência Tributária — Priorização da cobrança da dívida ativa de Palmas-TO (Opção D) |
| **Sprint e Período** | Sprint 4 — Modelo de IA e MVP (29/10/2026 a 11/11/2026) |
| **Módulo Âncora / Coordenação** | Módulo 6 — Introdução à Inteligência Artificial \| Prof. Dr. David Nadler Prata |
| **Equipe Executora** | Hyag, Ludmylla, Maiara, Sofia e Vitória (5 integrantes) |
| **Artefatos Entregues** | Repositório Git (branch mesclada), Jupyter Notebook documentado, modelos serializados em `/models` e Painel MVP em Streamlit |

---

## 1. Resumo Executivo

O presente relatório consolida as atividades desenvolvidas e os artefatos entregues pela equipe na Sprint 4 do Projeto Integrador. O objetivo central desta etapa consistiu em transformar a base de dados previamente tratada em inteligência acionável para a Secretaria Municipal de Finanças de Palmas (Sefin), por meio do treinamento de modelos preditivos de inadimplência, da estruturação de um sistema de scoring de recuperabilidade da dívida ativa e da disponibilização de um Produto Mínimo Viável (MVP) interativo para apoio à tomada de decisão dos analistas tributários.

Todos os quatro entregáveis previstos (E1 a E4) foram concluídos dentro do prazo estipulado (11/11/2026), com rastreabilidade integral garantida pelo histórico de commits individuais, revisão de pull requests e atualização do diário de bordo da equipe.

---

## 2. Metodologia de Treino e Modelos Baseline (Entregável E1)

Para assegurar a validade estatística e operacional da solução em ambiente real de cobrança tributária, a divisão dos conjuntos de treinamento, validação e teste foi estruturada rigorosamente por meio de um **split temporal**. A ordenação cronológica dos registros impediu qualquer vazamento de dados (*data leakage*), garantindo que informações de exercícios fiscais futuros não influenciassem o aprendizado de eventos passados:
- **Treinamento (Exercícios até 2022):** Ajuste de pesos e representações internas dos modelos.
- **Validação Temporal (Exercício 2023):** Seleção de hiperparâmetros e calibração de limiares de decisão.
- **Teste Cego Temporal (Exercício 2024):** Avaliação de desempenho em ambiente de simulação real fora da amostra.

Sobre a partição temporal estabelecida, foram treinados dois modelos baseline como linha de base comparativa: **Regressão Logística** e **Árvore de Decisão**. Ambos os algoritmos foram documentados no notebook principal, servindo de referência objetiva para aferir o ganho real de desempenho obtido com o avanço para modelos baseados em comitês de árvores.

---

## 3. Modelos Finais, Avaliação e Scoring (Entregáveis E2 e E3)

A partir da referência estabelecida pelos baselines, avançou-se para o treinamento de algoritmos de maior capacidade preditiva (**Random Forest** e **XGBoost**), submetidos a processo sistemático de tunagem de hiperparâmetros na base de validação temporal. A escolha do modelo final fundamentou-se no equilíbrio entre capacidade de generalização, estabilidade diante de desbalanceamento de classes e interpretabilidade das variáveis fiscais.

A avaliação completa foi extraída sobre o conjunto de teste temporal, contemplando as métricas de acurácia, precisão, recall, F1-score, ROC-AUC e matriz de confusão:

| Modelo | Acurácia | Precisão | Recall | F1-Score | ROC-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Regressão Logística (Baseline)** | 93,87% | 95,10% | 98,51% | 96,77% | 0,9077 |
| **Árvore de Decisão (Baseline)** | 81,06% | 99,63% | 80,00% | 88,74% | 0,8894 |
| **Random Forest (Campeão)** | 85,52% | 98,96% | 85,37% | 91,67% | 0,9154 |
| **XGBoost (Comitê de Gradiente)** | 84,96% | 98,62% | 85,07% | 91,35% | 0,9120 |

Paralelamente, foi implementado o modelo complementar de **scoring de recuperabilidade**, que converte as probabilidades estimadas e o perfil material do débito em três faixas operacionais de priorização:
1. **Alta Recuperabilidade ($Score \ge 68.0$):** Notificação digital amigável (WhatsApp, Pix, DDA bancário).
2. **Média Recuperabilidade ($42.0 \le Score < 68.0$):** Notificação postal, protesto cartorário e oferta do Programa REFIS Palmas.
3. **Baixa Recuperabilidade ($Score < 42.0$):** Execução fiscal prioritária e investigação patrimonial para penhora.

### Proteção Social Obrigatória (IPTU Social)
Em estrito respeito aos direitos dos contribuintes hipossuficientes, foi implementada regra inegociável de bloqueio automatizado de cobrança agressiva para munícipes isentos pelo **IPTU Social**, preservando a função distributiva do município.

### Métricas por Subgrupos e Preparação para a Sprint 5
Em conformidade com as diretrizes do projeto, as métricas de desempenho foram também calculadas e armazenadas de forma segmentada por subgrupos demográficos e territoriais (faixa de renda e região de Palmas), preparando a base quantitativa exigida para a auditoria de equidade (*fairness*) e elaboração do Relatório de Impacto Algorítmico (RIA) na Sprint 5. Todos os modelos finais e transformadores de pré-processamento foram serializados em formato `.joblib` e versionados no diretório `/models` do repositório.

---

## 4. Painel Interativo — MVP Sefin Palmas (Entregável E4)

Para tornar os modelos operacionais aos analistas da Sefin, foi desenvolvido um painel interativo em **Streamlit (`app.py`)** conectado diretamente aos artefatos serializados em `/models`. A aplicação permite demonstrar ao vivo o pipeline completo de inferência por meio de três módulos funcionais:

- **Ranking de Devedores:** Tabela dinâmica ordenada pelo score de recuperabilidade (e integrada à fila de prioridade Max-Heap $O(\log n)$), com filtros por faixa de risco (Alta, Média e Baixa) e perfil tributário para priorização imediata de cobrança.
- **Mapa de Calor de Inadimplência:** Visualização espacial e setorial (PyDeck/Deck.gl e Plotly) que evidencia a concentração de inadimplência por regiões e setores de Palmas-TO (Plano Diretor Norte, Plano Diretor Sul, Taquaralto, Jardins Aureny, Taquari e Taquaruçu).
- **Projeção de Arrecadação Potencial:** Simulador financeiro interativo que estima o montante recuperável a partir da atuação focalizada nos grupos de maior score, com modelagem de sensibilidade aos descontos da campanha REFIS Palmas e cenários orçamentários (Conservador, Realista e Otimista).

### Conformidade Ética, LGPD e Declaração de Dados
Todo o pipeline respeitou rigorosamente os princípios de minimização de dados e anonimização previstos na Lei Geral de Proteção de Dados (LGPD), utilizando exclusivamente fontes oficiais sem exposição de identificadores pessoais sensíveis. Encontra-se explicitamente declarado na abertura do Jupyter Notebook e na interface que a camada individual utilizada nesta fase possui natureza sintética, demonstrando a plena funcionalidade técnica e metodológica do pipeline desenvolvido.

---

## 5. Divisão de Responsabilidades e Entregas por Integrante

A execução da Sprint 4 foi organizada de forma modular entre os cinco membros da equipe, assegurando equilíbrio técnico e documental conforme registrado nos commits e pull requests do repositório:

| Integrante | Foco na Sprint | Atividades Executadas e Entregues |
| :--- | :--- | :--- |
| **Sofia Barros** | Split Temporal, Baselines e Classificação (E1, E2) | Implementou a divisão temporal sem vazamento de dados, treinou os modelos baseline (Regressão Logística e Árvore de Decisão), conduziu o treinamento e tunagem dos modelos principais (Random Forest/XGBoost) e exportou os artefatos para `/models`. |
| **Hyag Queiroz** | Scoring, Pipeline e Gestão Git (E2, E3) | Desenvolveu o modelo complementar de scoring de recuperabilidade (faixas alta, média e baixa), integrou o carregamento dos modelos serializados ao backend do painel e gerenciou os branches e pull requests no repositório Git. |
| **Vitória Alves** | Interface do MVP em Streamlit (E4) | Construiu o painel interativo em Streamlit conectado ao pipeline real, implementando o ranking de devedores por score, o mapa de calor de inadimplência por setor/região e o módulo de projeção de arrecadação potencial. |
| **Maiara Xerente** | Métricas, Subgrupos e Análise Técnica (E2, E3) | Extraiu e interpretou as métricas completas (acurácia, precisão, recall, F1 e matriz de confusão), gerou os recortes de desempenho por faixa de renda e região (base para a Sprint 5) e redigiu as justificativas algorítmicas e de conformidade LGPD. |
| **Ludmylla Teixeira** | Consolidação, Auditoria e Entrega (E3, Fechamento) | Estruturou e revisou a trilha narrativa completa no Jupyter Notebook (EDA → pré-processamento → treino → avaliação), auditou o diário de bordo e o histórico de commits individuais, realizou o merge final e submeteu o link à coordenação. |

---

## Conclusão e Próximos Passos
Com a conclusão da Sprint 4, a equipe dispõe de um pipeline preditivo reprodutível e de um MVP funcional. Na Sprint 5, os recortes de desempenho por subgrupo já salvos serão utilizados para conduzir a análise formal de *fairness* e estruturar o Relatório de Impacto Algorítmico (RIA).
