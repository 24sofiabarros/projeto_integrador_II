from dataclasses import dataclass
from typing import Optional

@dataclass
class Contribuinte:
    cpf_cnpj: str
    nome: str
    possui_iptu_social: bool = False  # Regra de proteção ao IPTU Social

@dataclass
class DebitoIPTU:
    id_debito: int
    cpf_contribuinte: str
    valor_devido: float
    ano_exercicio: int
    score_inadimplencia: Optional[float] = None  # Calculado pela IA
