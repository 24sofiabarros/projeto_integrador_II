# Resumo de Entregas e Consolidação Técnica - Sprint 2 (Ciclo de Outubro/2026)

## 1. Visão Geral do Ciclo

Este documento consolida as entregas e evoluções técnicas realizadas pela equipe no ciclo de **Outubro de 2026** no âmbito da **Sprint 2** do Projeto Integrador II (SITRIB - Sistema de Inteligência Tributária da Prefeitura Municipal de Palmas-TO).

A Sprint 2 marca a transição da modelagem conceitual e levantamento de requisitos (Sprint 1) para a **implementação de infraestrutura de dados relacional (3FN)**, **estruturas de dados avançadas em Python com análise de complexidade (Big-O)** e a **especificação arquitetural e de segurança para integração de APIs externas**.

---

## 2. Quadro de Entregáveis da Sprint 2

| Entregável | Descrição Principal | Artefatos e Códigos Associados | Responsáveis no Ciclo |
| :--- | :--- | :--- | :--- |
| **E1 - Banco de Dados Relacional (3FN)** | Modelagem física em 3ª Forma Normal, DDL de tabelas com constraints, carga inicial de testes e consultas SQL de validação. | `docs/diagrama_er.png`<br>`src/banco/schema_3fn.sql`<br>`src/banco/seed_piloto.sql`<br>`src/banco/consultas_validacao.sql` | Sofia Barros / Equipe Técnica |
| **E2 - Algoritmos e Estruturas de Dados Avançadas** | Implementação de Grafo (BFS), Heap Máximo (Fila de Prioridade) e Tabela Hash $O(1)$ com testes integrados e análise assintótica Big-O. | `src/estruturas/arquitetura_dados.py`<br>`docs/arquitetura_dados.md` | Sofia Barros / Equipe Técnica |
| **E3 - Integração com API REST e Segurança** | Mapeamento de rotas governamentais da Sefin Palmas, protocolos de segurança LGPD, política de autenticação Bearer Token e exemplos funcionais. | `docs/integracao_api.md` | Sofia Barros & Hyago Queiroz |

---

## 3. Detalhamento dos Módulos Desenvolvidos

### 3.1. Entregável E1: Modelagem Relacional e Banco de Dados (3FN)

A camada de persistência foi desenhada para garantir integridade referencial, eliminação de redundâncias e alta consistência dos dados fazendários municipais:

1. **Diagrama Entidade-Relacionamento (`docs/diagrama_er.png`):**
   * Representação visual das entidades centrais: `contribuinte`, `imovel` e `divida_ativa`.
2. **Normalização e DDL (`src/banco/schema_3fn.sql`):**
   * **Tabela `contribuinte`:** Chave primária substituta, `cpf_cnpj` com restrição de unicidade e flag booleana de política pública (`isencao_iptu_social`).
   * **Tabela `imovel`:** Identificação por `inscricao_imobiliaria`, relacionamento $1:N$ com contribuinte via chave estrangeira com integridade referencial (`ON DELETE RESTRICT ON UPDATE CASCADE`).
   * **Tabela `divida_ativa`:** Registro de lançamentos tributários, restrição de domínio `CHECK` para tributos (`IPTU`, `ISS`, `ITBI`, `TAXAS`), status de cobrança e campo preditivo `score_recuperabilidade` (0 a 100).
3. **Massa de Testes Piloto (`src/banco/seed_piloto.sql`):**
   * População de dados representativos do cenário imobiliário de Palmas (Plano Diretor Sul/Norte, Taquaralto), contemplando contribuintes regulares, grandes devedores e beneficiários do IPTU Social.
4. **Consultas de Validação Fiscal (`src/banco/consultas_validacao.sql`):**
   * Query analítica com `JOIN` entre as 3 tabelas, demonstrando consolidação de débitos, identificação de isenções e ordenação por score preditivo.

---

### 3.2. Entregável E2: Algoritmos e Estruturas de Dados Avançadas (Python)

Implementação em Python puro (`src/estruturas/arquitetura_dados.py`) para processamento em memória e alta performance, acompanhada de documentação analítica de complexidade assintótica (`docs/arquitetura_dados.md`):

1. **Grafo de Relações Tributárias (`GrafoRelacoesTributarias`):**
   * **Objetivo:** Mapear redes de conexões entre CPFs/CNPJs e inscrições imobiliárias para identificar grupos econômicos e confusão patrimonial.
   * **Algoritmo:** Busca em Largura (BFS - *Breadth-First Search*).
   * **Complexidade Temporal:** $O(V + E)$, onde $V$ são os vértices (pessoas/imóveis) e $E$ as relações tributárias.
2. **Fila de Cobrança Preditiva com Heap Máximo (`FilaCobrancaHeap`):**
   * **Objetivo:** Priorizar automaticamente as ações fiscais e ajuizamento de débitos pelo maior score de recuperabilidade.
   * **Regra de Negócio Crítica:** Exclusão automática de contribuintes com flag `isencao_iptu_social = True`, protegendo cidadãos vulneráveis.
   * **Complexidade Temporal:** Inserção $O(\log N)$ e Extração de topo $O(\log N)$ via inversão de pesos com `heapq`.
3. **Tabela Hash de Inscrições Imobiliárias (`TabelaHashInscricoes`):**
   * **Objetivo:** Indexação e recuperação em tempo constante de débitos a partir do código cadastral do imóvel.
   * **Tratamento de Colisão:** Encadeamento direto (*Separate Chaining*).
   * **Complexidade Temporal:** $O(1)$ médio para inserção e busca.

---

### 3.3. Entregável E3: Integração de APIs Externas e Mecanismo de Autenticação

A documentação em `docs/integracao_api.md` estabelece a base para consumo seguro das APIs da Secretaria Municipal de Finanças (Sefin de Palmas):

1. **Rotas Mapeadas:**
   * `GET /arrecadacao/iptu`: Histórico de arrecadação imobiliária.
   * `GET /arrecadacao/iss`: Dados de recolhimento de prestadores de serviços e autônomos.
   * `GET /divida-ativa/devedores`: Consulta de títulos em cobrança executiva com score.
2. **Mecanismo de Autenticação Detalhado (Contribuição de Hyago Queiroz):**
   * **Padrão Utilizado:** Bearer Token via cabeçalho HTTP (`Authorization: Bearer <TOKEN>`) sobre canal criptografado HTTPS (TLS 1.3 obrigatório).
   * **Fluxo de Autenticação:** Convênio institucional $\rightarrow$ Carregamento via `.env` $\rightarrow$ Envio no cabeçalho $\rightarrow$ Validação de escopo pelo gateway municipal.
   * **Segurança e Proteção de Segredos:** Proibição irrestrita de credenciais *hardcoded*; segregação no arquivo `.env` (ignorado no `.gitignore`); sanitização de logs de auditoria contra vazamento de cabeçalhos.
   * **Tratamento de Erros:**
     * `HTTP 401 Unauthorized`: Bloqueio imediato sem retentativas automáticas cegas (prevenção contra ataques de força bruta).
     * `HTTP 403 Forbidden`: Registro de auditoria por privilégios insuficientes.
   * **Exemplos Operacionais:** Modelos de chamada via cURL e script cliente conceitual em Python utilizando `os.getenv` e `requests`.

---

## 4. Matriz de Rastreabilidade com os Requisitos da Sprint 1

| Requisito Original (Sprint 1) | Implementação Concluída na Sprint 2 |
| :--- | :--- |
| **RF01 - RBAC e Autenticação** | Diretrizes de autenticação institucional e gestão de tokens em `docs/integracao_api.md`. |
| **RF02 - Ingestão de APIs Externas** | Mapeamento de endpoints Sefin, tratamento de HTTP 401/403 e exemplos em Python/cURL. |
| **RF03 / RF04 - Cruzamento e Detecção** | `GrafoRelacoesTributarias` (BFS) para identificação de grupos econômicos e imóveis vinculados. |
| **RF05 / RF06 - Dashboard e Consulta Unificada** | `TabelaHashInscricoes` com busca $O(1)$ e schema relacional normalizado 3FN. |
| **RF07 - Cobrança da Dívida Ativa** | `FilaCobrancaHeap` com ordenação por score e filtro social de IPTU. |
| **RF10 - Trilha de Auditoria e LGPD** | Anonimização de dados, proibição de chaves em logs e conformidade documentada no Entregável E3. |

---

## 5. Histórico e Contribuições Técnicas da Equipe (Outubro/2026)

* **Sofia Barros:**
  * Commit `4544edc`: Criação dos scripts DDL 3FN (`schema_3fn.sql`), carga de dados (`seed_piloto.sql`) e consultas (`consultas_validacao.sql`).
  * Commit `dc6de6e`: Inclusão do diagrama de Entidade-Relacionamento (`docs/diagrama_er.png`).
  * Commit `0ce7a1b`: Implementação das estruturas de dados em Python (`src/estruturas/arquitetura_dados.py`) e documentos de arquitetura e integração inicial.
* **Hyago Queiroz:**
  * Commit `11e1d98`: Especificação completa e aprofundada do mecanismo de autenticação institucional via Bearer Token, políticas de segurança, tratamento de erros e exemplos em Python/cURL em `docs/integracao_api.md`.
* **Vitória Alves:**
  * Acompanhamento e validação de artefatos de engenharia de software e diagramas.
* **Ludmylla Teixeira & Maiara Ktidi Xerente:**
  * Revisão da estruturação MVC, consolidação das branches de entrega e integração dos entregáveis para Pull Request unificado na branch principal.
