import heapq
from typing import Dict, List, Optional, Tuple, Set

# =====================================================================
# 1. GRAFO DE RELAÇÕES ENTRE CONTRIBUINTES E IMÓVEIS
# =====================================================================
class GrafoRelacoesTributarias:
    """
    Representa a rede de conexões entre Contribuintes e seus Imóveis/Empresas.
    Permite identificar grupos econômicos e propriedades vinculadas ao mesmo CPF/CNPJ.
    """
    def __init__(self):
        self.adjacencia: Dict[str, Set[str]] = {}

    def adicionar_vertice(self, vertice: str):
        if vertice not in self.adjacencia:
            self.adjacencia[vertice] = set()

    def adicionar_aresta(self, u: str, v: str):
        self.adicionar_vertice(u)
        self.adicionar_vertice(v)
        self.adjacencia[u].add(v)
        self.adjacencia[v].add(u)  # Grafo não-direcionado

    def buscar_grupo_economico(self, vertice_inicial: str) -> List[str]:
        """Realiza Busca em Largura (BFS) para mapear todo o grupo de imóveis/sócios."""
        if vertice_inicial not in self.adjacencia:
            return []
        
        visitados = set([vertice_inicial])
        fila = [vertice_inicial]
        grupo = []

        while fila:
            atual = fila.pop(0)
            grupo.append(atual)
            for vizinho in self.adjacencia[atual]:
                if vizinho not in visitados:
                    visitados.add(vizinho)
                    fila.append(vizinho)
        return grupo


# =====================================================================
# 2. FILA DE PRIORIDADE COM HEAP MÁXIMO (SCORE DE RECUPERABILIDADE)
# =====================================================================
class FilaCobrancaHeap:
    """
    Heap Máximo para organizar a fila de cobrança da Dívida Ativa.
    Prioriza débitos com maior score de recuperabilidade.
    Exclui automaticamente beneficiários do IPTU Social.
    """
    def __init__(self):
        self.heap: List[Tuple[float, str, str, float, bool]] = []

    def inserir_divida(self, score: float, id_divida: str, inscricao: str, valor: float, iptu_social: bool):
        # Regra de Negócio: Isentos do IPTU Social não entram na fila preditiva de cobrança
        if iptu_social:
            return
        # heapq no Python é Min-Heap por padrão. Invertemos o sinal do score para simular Max-Heap.
        heapq.heappush(self.heap, (-score, id_divida, inscricao, valor))

    def extrair_proxima_cobranca(self) -> Optional[Tuple[float, str, str, float]]:
        if not self.heap:
            return None
        neg_score, id_divida, inscricao, valor = heapq.heappop(self.heap)
        return (-neg_score, id_divida, inscricao, valor)


# =====================================================================
# 3. TABELA HASH DE INDEXAÇÃO DE INSCRIÇÕES IMOBILIÁRIAS
# =====================================================================
class TabelaHashInscricoes:
    """
    Tabela Hash com Encadeamento para busca O(1) de débitos por Inscrição Imobiliária.
    """
    def __init__(self, capacidade: int = 101):
        self.capacidade = capacidade
        self.tabela: List[List[Tuple[str, dict]]] = [[] for _ in range(capacidade)]

    def _hash(self, chave: str) -> int:
        return hash(chave) % self.capacidade

    def inserir(self, inscricao: str, dados_divida: dict):
        indice = self._hash(inscricao)
        for i, (k, v) in enumerate(self.tabela[indice]):
            if k == inscricao:
                self.tabela[indice][i] = (inscricao, dados_divida)
                return
        self.tabela[indice].append((inscricao, dados_divida))

    def buscar(self, inscricao: str) -> Optional[dict]:
        indice = self._hash(inscricao)
        for k, v in self.tabela[indice]:
            if k == inscricao:
                return v
        return None


# =====================================================================
# TESTE PILOTO DAS ESTRUTURAS DE DADOS
# =====================================================================
if __name__ == "__main__":
    print("=== TESTANDO GRAFO DE GRUPOS ECONÔMICOS ===")
    grafo = GrafoRelacoesTributarias()
    grafo.adicionar_aresta("CPF:111.222.333-00", "IMP-104S-01")
    grafo.adicionar_aresta("CPF:111.222.333-00", "IMP-104S-02")
    print("Vínculos de João Silva:", grafo.buscar_grupo_economico("CPF:111.222.333-00"))

    print("\n=== TESTANDO FILA HEAP DE COBRANÇA PRIORIZADA ===")
    fila = FilaCobrancaHeap()
    fila.inserir_divida(88.50, "DIV-001", "IMP-104S-01", 2500.50, False)
    fila.inserir_divida(20.00, "DIV-002", "IMP-TAQ-05", 850.00, True)   # IPTU Social (Ignorado)
    fila.inserir_divida(94.20, "DIV-003", "IMP-501N-09", 15400.00, False)

    proximo = fila.extrair_proxima_cobranca()
    print(f"Próxima cobrança prioritária: Score {proximo[0]} - Dívida {proximo[1]} - Valor R${proximo[3]}")

    print("\n=== TESTANDO TABELA HASH DE INDEXAÇÃO O(1) ===")
    hash_tab = TabelaHashInscricoes()
    hash_tab.inserir("IMP-501N-09", {"tributo": "ISS", "valor": 15400.00, "status": "Em Aberto"})
    print("Busca rápida IMP-501N-09:", hash_tab.buscar("IMP-501N-09"))