# Arquitetura e Estruturas de Dados Avançadas (Módulo 3)

## Visão Geral
Para garantir a escalabilidade do sistema de Inteligência Tributária da Sefin de Palmas-TO, foram implementadas três estruturas de dados fundamentais em Python (`src/estruturas/arquitetura_dados.py`):

1. **Grafo não-direcionado (`GrafoRelacoesTributarias`):** Mapeia conexões entre contribuintes (CPF/CNPJ) e múltiplos imóveis/empresas para identificar grupos econômicos e corresponsabilidade fiscal.
2. **Fila de Prioridade em Heap Máximo (`FilaCobrancaHeap`):** Mantém a ordem dinâmica das ações fiscais com base no *score* de recuperabilidade da dívida, ignorando contribuintes isentos do IPTU Social.
3. **Tabela Hash (`TabelaHashInscricoes`):** Indexação em tempo constante $O(1)$ para consultas rápidas por inscrição imobiliária ou CPF/CNPJ.

---

## Análise de Complexidade Computacional (Big-O)

| Estrutura de Dados | Operação Principal | Complexidade Temporal | Justificativa Técnica |
| :--- | :--- | :---: | :--- |
| **Grafo (BFS)** | Busca de Grupo Econômico | $O(V + E)$ | $V$ representa contribuintes/imóveis e $E$ as relações entre eles. |
| **Heap Máximo** | Inserção de Novo Débito | $O(\log N)$ | Manutenção da propriedade de heap binário. |
| **Heap Máximo** | Extração do Maior Score | $O(\log N)$ | Remoção da raiz e reordenamento do heap. |
| **Tabela Hash** | Busca por Inscrição | $O(1)$ médio | Distribuição uniforme via função hash com tratamento de colisões por encadeamento. |