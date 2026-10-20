"""
==============================================================================
SITRIB - Sistema de Inteligência Tributária (Sefin Palmas-TO)
Módulo: Coleta Automatizada via API REST (Sprint 3 - Tarefa E1)
==============================================================================
Responsável: Hyago Queiroz (Product Owner)
Descrição:
  Script de ingestão de dados tributários municipais (IPTU, ISS, Dívida Ativa)
  com autenticação por Bearer Token, paginação automática, controle ético de
  taxa de requisição (rate limiting), tratamento de erros HTTP (401, 403, 429),
  anonimização LGPD em memória e persistência datada em data/bruto/.
==============================================================================
"""

import json
import logging
import os
import re
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

try:
    import requests
except ImportError:
    requests = None

# Carregamento de variáveis de ambiente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configuração de logging seguro (sem expor credenciais)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ColetorAPISefin")


# ==============================================================================
# EXCEÇÕES PERSONALIZADAS DE COLETA
# ==============================================================================
class ColetaAPIError(Exception):
    """Exceção base para erros ocorridos durante a coleta via API."""
    pass


class AutenticacaoInvalidaError(ColetaAPIError):
    """Disparada quando a API retorna HTTP 401 (Unauthorized)."""
    pass


class AcessoNegadoError(ColetaAPIError):
    """Disparada quando a API retorna HTTP 403 (Forbidden)."""
    pass


class RateLimitExcedidoError(ColetaAPIError):
    """Disparada quando a API retorna HTTP 429 e as retentativas falham."""
    pass


# ==============================================================================
# FUNÇÕES DE ANONIMIZAÇÃO E CONFORMIDADE LGPD
# ==============================================================================
def anonimizar_cpf(cpf: str) -> str:
    """
    Anonimiza CPF conforme diretrizes da LGPD especificadas no projeto:
    Mascara os 6 primeiros dígitos e os 2 dígitos verificadores,
    preservando apenas o bloco central: ***.***.123-**
    
    Exemplos:
      '111.222.333-00' -> '***.***.333-**'
      '12345678900'    -> '***.***.789-**'
    """
    if not cpf:
        return ""
    
    digitos = re.sub(r"\D", "", str(cpf))
    if len(digitos) == 11:
        bloco_central = digitos[6:9]
        return f"***.***.{bloco_central}-**"
    
    # Caso não tenha 11 dígitos, aplica mascaramento genérico
    return "***.***.***-**"


def anonimizar_cnpj(cnpj: str) -> str:
    """
    Anonimiza CNPJ conforme diretrizes da LGPD especificadas no projeto:
    Preserva a raiz cadastral da empresa (primeiros 8 dígitos) e oculta
    a filial e os dígitos verificadores: 12.345.678/****-**
    
    Exemplos:
      '33.444.555/0001-66' -> '33.444.555/****-**'
      '12345678000199'     -> '12.345.678/****-**'
    """
    if not cnpj:
        return ""
    
    digitos = re.sub(r"\D", "", str(cnpj))
    if len(digitos) == 14:
        parte1 = digitos[0:2]
        parte2 = digitos[2:5]
        parte3 = digitos[5:8]
        return f"{parte1}.{parte2}.{parte3}/****-**"
    
    # Caso não tenha 14 dígitos, aplica mascaramento genérico
    return "**.***.***/****-**"


def anonimizar_documento(doc: str) -> str:
    """Identifica dinamicamente se o documento é CPF ou CNPJ e aplica a anonimização."""
    if not doc:
        return ""
    digitos = re.sub(r"\D", "", str(doc))
    if len(digitos) == 11:
        return anonimizar_cpf(doc)
    elif len(digitos) == 14:
        return anonimizar_cnpj(doc)
    return "***.***"


def eh_campo_sensivel_expurgo(chave: str) -> bool:
    """Verifica se o campo representa dado pessoal sensível/desnecessário (telefones, e-mails)."""
    c = chave.lower()
    # Telefones particulares/devedor/contato (qualquer campo telefônico)
    if any(termo in c for termo in ["telefone", "celular", "phone", "whatsapp", "tel"]):
        return True
    # E-mails pessoais e genéricos
    if any(termo in c for termo in ["email_pessoal", "email_particular", "email_devedor", "email_secundario"]):
        return True
    if c in {"email", "e_mail", "mail"}:
        return True
    return False

CAMPOS_DOCUMENTO = {
    "cpf",
    "cnpj",
    "cpf_cnpj",
    "cpf_contribuinte",
    "documento",
    "cpf_cnpj_alvo",
    "cpf_cnpj_proprietario",
}


def anonimizar_registro_lgpd(registro: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplica as regras de proteção LGPD a um dicionário de registro:
    1. Mascara CPFs e CNPJs;
    2. Expulsa dados de contato sensíveis e desnecessários (telefones, e-mails).
    """
    if not isinstance(registro, dict):
        return registro

    registro_limpo: Dict[str, Any] = {}

    for chave, valor in registro.items():
        chave_lower = chave.lower()

        # 1. Descarte estrito de contatos pessoais desnecessários
        if eh_campo_sensivel_expurgo(chave_lower):
            continue

        # 2. Anonimização de documentos de identificação
        if chave_lower in CAMPOS_DOCUMENTO and isinstance(valor, str):
            registro_limpo[chave] = anonimizar_documento(valor)
        elif isinstance(valor, dict):
            registro_limpo[chave] = anonimizar_registro_lgpd(valor)
        elif isinstance(valor, list):
            registro_limpo[chave] = [
                anonimizar_registro_lgpd(item) if isinstance(item, dict) else item
                for item in valor
            ]
        else:
            registro_limpo[chave] = valor

    return registro_limpo


# ==============================================================================
# CLASSE PRINCIPAL: COLETOR DE API REST (SEFIN PALMAS)
# ==============================================================================
class ColetorAPISefin:
    """
    Cliente REST automatizado para ingestão ética e segura de dados tributários
    da Secretaria Municipal de Finanças de Palmas (SITRIB).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        rate_limit_delay: Optional[float] = None,
        timeout: Optional[int] = None,
    ):
        # 1. Resolução da URL Base
        self.base_url = (
            base_url
            or os.getenv("SEFIN_API_BASE_URL")
            or "https://integracao.palmas.to.gov.br/apirest"
        ).rstrip("/")

        # 2. Resolução do Bearer Token via .env
        self.token = token or os.getenv("SEFIN_API_TOKEN")
        if not self.token:
            raise ValueError(
                "Variável de ambiente SEFIN_API_TOKEN não configurada. "
                "Defina o token no arquivo .env antes de executar a coleta."
            )

        # 3. Rate Limit e Timeout
        env_delay = os.getenv("SEFIN_RATE_LIMIT_DELAY")
        self.rate_limit_delay = (
            rate_limit_delay
            if rate_limit_delay is not None
            else (float(env_delay) if env_delay else 1.0)
        )
        # Garantia do atraso ético mínimo de 1.0 segundo
        if self.rate_limit_delay < 1.0:
            logger.warning(
                "Rate limit inferior a 1.0s configurado (%ss). Ajustando para 1.0s para consumo ético.",
                self.rate_limit_delay,
            )
            self.rate_limit_delay = 1.0

        env_timeout = os.getenv("SEFIN_API_TIMEOUT")
        self.timeout = timeout if timeout is not None else (int(env_timeout) if env_timeout else 15)

        # Timestamp da última requisição para controle de taxa
        self._ultima_requisicao = 0.0

    def _obter_headers(self) -> Dict[str, str]:
        """Gera os cabeçalhos HTTP com autenticação Bearer Token."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "User-Agent": "SITRIB-ETL-Client/1.0 (Prefeitura de Palmas - Sefin)",
        }

    def _aplicar_rate_limit(self) -> None:
        """Assegura intervalo mínimo de 1.0 segundo entre requisições consecutivas."""
        agora = time.time()
        tempo_decorrido = agora - self._ultima_requisicao
        if tempo_decorrido < self.rate_limit_delay:
            tempo_espera = self.rate_limit_delay - tempo_decorrido
            logger.debug("Rate-limiting: aguardando %.2fs antes da próxima requisição.", tempo_espera)
            time.sleep(tempo_espera)
        self._ultima_requisicao = time.time()

    def _fazer_requisicao(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, max_retentativas: int = 3
    ) -> Dict[str, Any]:
        """
        Executa uma requisição HTTP GET com controle ético, tratamento de erros e retentativas em HTTP 429.
        """
        url_completa = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._obter_headers()

        tentativa = 0
        while tentativa < max_retentativas:
            tentativa += 1
            self._aplicar_rate_limit()

            logger.info("Requisição GET -> %s (Params: %s) [Tentativa %d/%d]", url_completa, params or {}, tentativa, max_retentativas)

            try:
                response = requests.get(
                    url_completa,
                    headers=headers,
                    params=params,
                    timeout=self.timeout,
                )

                # Tratamento de HTTP 401 - Unauthorized
                if response.status_code == 401:
                    logger.error("HTTP 401: Falha de autenticação na API Sefin. Verifique a chave SEFIN_API_TOKEN no .env.")
                    raise AutenticacaoInvalidaError(
                        "Falha de autenticação na API Sefin: Token inválido ou expirado (HTTP 401)."
                    )

                # Tratamento de HTTP 403 - Forbidden
                if response.status_code == 403:
                    logger.error("HTTP 403: Acesso negado para o endpoint %s.", endpoint)
                    raise AcessoNegadoError(
                        f"Acesso negado: Token sem privilégios para o endpoint '{endpoint}' (HTTP 403)."
                    )

                # Tratamento de HTTP 429 - Too Many Requests (com retentativa)
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    tempo_espera = float(retry_after) if retry_after else (2.0 * tentativa)
                    logger.warning(
                        "HTTP 429 (Too Many Requests). Aguardando %.1fs antes de retentar...",
                        tempo_espera,
                    )
                    time.sleep(tempo_espera)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.RequestException as e:
                # Se for erro de autenticação ou autorização já capturado, propaga
                if isinstance(e, (AutenticacaoInvalidaError, AcessoNegadoError)):
                    raise
                logger.error("Erro na comunicação com a API Sefin (%s): %s", url_completa, str(e))
                if tentativa >= max_retentativas:
                    raise ColetaAPIError(f"Falha de comunicação persistente após {max_retentativas} tentativas: {e}") from e
                time.sleep(1.0 * tentativa)

        raise RateLimitExcedidoError(f"Número máximo de retentativas atingido para {endpoint} (HTTP 429).")

    def coletar_paginado(
        self,
        endpoint: str,
        params_base: Optional[Dict[str, Any]] = None,
        max_paginas: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Itera automaticamente sobre as páginas da API enquanto houver registros
        disponíveis e acumula todos os dados retornados.
        """
        registros_totais: List[Dict[str, Any]] = []
        pagina_atual = 1
        params = dict(params_base or {})

        logger.info("Iniciando coleta paginada no endpoint '%s'...", endpoint)

        while pagina_atual <= max_paginas:
            params["page"] = pagina_atual
            resposta = self._fazer_requisicao(endpoint, params=params)

            # Extração dos registros retornados (suporte a formato envelopado ou lista direta)
            itens = []
            tem_proxima = False

            if isinstance(resposta, list):
                itens = resposta
                tem_proxima = len(itens) > 0
            elif isinstance(resposta, dict):
                # Formato padrão SITRIB: {"dados": [...], "tem_proxima": bool, "total_paginas": int}
                itens = resposta.get("dados") or resposta.get("itens") or resposta.get("registros") or []
                total_paginas = resposta.get("total_paginas")
                if "tem_proxima" in resposta:
                    tem_proxima = bool(resposta["tem_proxima"])
                elif total_paginas:
                    tem_proxima = pagina_atual < total_paginas
                else:
                    tem_proxima = len(itens) > 0
            else:
                logger.warning("Resposta inesperada no endpoint %s: %s", endpoint, type(resposta))
                break

            if not itens:
                logger.info("Nenhum registro retornado na página %d. Encerrando paginação.", pagina_atual)
                break

            registros_totais.extend(itens)
            logger.info("Página %d coletada com sucesso: %d registros obtidos (Acumulado: %d).", pagina_atual, len(itens), len(registros_totais))

            if not tem_proxima:
                logger.info("Última página alcançada (página %d). Paginação finalizada.", pagina_atual)
                break

            pagina_atual += 1

        return registros_totais

    def persistir_dados(
        self,
        dados: List[Dict[str, Any]],
        categoria: str,
        diretorio_destino: str = "data/bruto",
    ) -> Path:
        """
        Aplica anonimização LGPD e salva os dados brutos em formato JSON datado:
        data/bruto/{categoria}_YYYYMMDD_HHMMSS.json
        """
        caminho_dir = Path(diretorio_destino)
        caminho_dir.mkdir(parents=True, exist_ok=True)

        # 1. Anonimização LGPD prévia antes da escrita em disco
        logger.info("Aplicando anonimização LGPD e expurgo de dados sensíveis na categoria '%s'...", categoria)
        dados_anonimizados = [anonimizar_registro_lgpd(reg) for reg in dados]

        # 2. Formatação do nome de arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"{categoria}_{timestamp}.json"
        caminho_arquivo = caminho_dir / nome_arquivo

        # 3. Gravação segura em disco
        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "categoria": categoria,
                    "timestamp_coleta": datetime.now().isoformat(),
                    "total_registros": len(dados_anonimizados),
                    "dados": dados_anonimizados,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        logger.info("Dados brutos persistidos com sucesso em: %s (%d registros).", caminho_arquivo, len(dados_anonimizados))
        return caminho_arquivo

    def coletar_todas_categorias(
        self,
        diretorio_destino: str = "data/bruto",
    ) -> Dict[str, Path]:
        """
        Executa o pipeline completo de coleta para as três categorias fazendárias:
        - IPTU: /arrecadacao/iptu
        - ISS:  /arrecadacao/iss
        - Dívida Ativa: /divida-ativa/devedores
        """
        endpoints = {
            "iptu": "arrecadacao/iptu",
            "iss": "arrecadacao/iss",
            "divida_ativa": "divida-ativa/devedores",
        }

        arquivos_gerados: Dict[str, Path] = {}

        for categoria, endpoint in endpoints.items():
            logger.info("=== INICIANDO COLETA: %s ===", categoria.upper())
            registros = self.coletar_paginado(endpoint)
            caminho = self.persistir_dados(registros, categoria, diretorio_destino)
            arquivos_gerados[categoria] = caminho

        logger.info("=== COLETA DE TODAS AS CATEGORIAS CONCLUÍDA COM SUCESSO ===")
        return arquivos_gerados


# ==============================================================================
# SERVIDOR SIMULADOR REST CONTROLADO (MOCK PARA TESTES E DEMONSTRAÇÃO)
# ==============================================================================
DADOS_SIMULADOS_IPTU = [
    {
        "id_lancamento": 101,
        "inscricao_imobiliaria": "IMP-104S-01",
        "exercicio": 2024,
        "valor_lancado": 2500.50,
        "cpf_contribuinte": "111.222.333-00",
        "nome": "João Silva",
        "telefone": "(63) 99111-2222",
        "email": "joao.silva@emailpessoal.com",
        "isencao_social": False,
        "logradouro": "Rua NE 01, Lote 12",
        "setor": "104 Sul",
    },
    {
        "id_lancamento": 102,
        "inscricao_imobiliaria": "IMP-TAQ-05",
        "exercicio": 2024,
        "valor_lancado": 850.00,
        "cpf_contribuinte": "222.333.444-11",
        "nome": "Maria Oliveira",
        "telefone": "(63) 99222-3333",
        "email": "maria.social@emailpessoal.com",
        "isencao_social": True,
        "logradouro": "Av. Tocantins, Quadra 10",
        "setor": "Setor Taquaralto",
    },
    {
        "id_lancamento": 103,
        "inscricao_imobiliaria": "IMP-104S-02",
        "exercicio": 2024,
        "valor_lancado": 3100.00,
        "cpf_contribuinte": "111.222.333-00",
        "nome": "João Silva",
        "telefone": "(63) 99111-2222",
        "email": "joao.silva@emailpessoal.com",
        "isencao_social": False,
        "logradouro": "Rua NE 03, Lote 15",
        "setor": "104 Sul",
    },
]

DADOS_SIMULADOS_ISS = [
    {
        "id_declaracao": 201,
        "inscricao_municipal": "ISS-PALMAS-001",
        "cnpj": "33.444.555/0001-66",
        "razao_social": "Comércio de Alimentos Palmas LTDA",
        "competencia": "2024/09",
        "faturamento_declarado": 154000.00,
        "iss_apurado": 7700.00,
        "telefone_contato": "(63) 3215-0001",
        "email_comercial": "contabil@alimentos.com.br",
        "email_pessoal": "socio@emailpessoal.com",
    },
    {
        "id_declaracao": 202,
        "inscricao_municipal": "ISS-PALMAS-002",
        "cnpj": "12.345.678/0001-99",
        "razao_social": "Tecnologia e Serviços Tocantins LTDA",
        "competencia": "2024/09",
        "faturamento_declarado": 89000.00,
        "iss_apurado": 4450.00,
        "telefone": "(63) 3216-0002",
        "email": "diretoria@techto.com.br",
    },
]

DADOS_SIMULADOS_DIVIDA = [
    {
        "id_divida": "DIV-001",
        "inscricao_imobiliaria": "IMP-104S-01",
        "tipo_tributo": "IPTU",
        "exercicio": 2023,
        "valor_consolidado": 2500.50,
        "score_recuperabilidade": 88.50,
        "status_cobranca": "Em Aberto",
        "cpf_cnpj": "111.222.333-00",
        "telefone_devedor": "(63) 98888-7777",
    },
    {
        "id_divida": "DIV-002",
        "inscricao_imobiliaria": "IMP-TAQ-05",
        "tipo_tributo": "IPTU",
        "exercicio": 2023,
        "valor_consolidado": 850.00,
        "score_recuperabilidade": 20.00,
        "status_cobranca": "Em Aberto",
        "cpf_cnpj": "222.333.444-11",
        "telefone_devedor": "(63) 98777-6666",
    },
    {
        "id_divida": "DIV-003",
        "inscricao_imobiliaria": "IMP-501N-09",
        "tipo_tributo": "ISS",
        "exercicio": 2023,
        "valor_consolidado": 15400.00,
        "score_recuperabilidade": 94.20,
        "status_cobranca": "Em Aberto",
        "cpf_cnpj": "33.444.555/0001-66",
        "email_cobranca": "juridico@alimentos.com.br",
    },
]


class MockSefinHandler(BaseHTTPRequestHandler):
    """Manipulador HTTP REST para simulação da API Sefin Palmas."""

    _ultimo_tempo_requisicao = 0.0

    def log_message(self, format, *args):
        # Silencia logs padrão do HTTP handler no console para não poluir
        pass

    def _enviar_json(self, status: int, payload: Any, headers: Optional[Dict[str, str]] = None):
        corpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        if headers:
            for k, v in headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        url_parsed = urlparse(self.path)
        path = url_parsed.path.rstrip("/")
        query_params = parse_qs(url_parsed.query)

        # 1. Verificação de Autenticação Bearer
        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            self._enviar_json(401, {"erro": "Não autorizado: Cabeçalho Authorization com Bearer token ausente."})
            return

        token_enviado = auth_header.split(" ", 1)[1].strip()
        if not token_enviado:
            self._enviar_json(401, {"erro": "Não autorizado: Token Bearer vazio ou inválido."})
            return

        if token_enviado == "token_invalido":
            self._enviar_json(401, {"erro": "Não autorizado: Token institucional inválido ou expirado."})
            return

        if token_enviado == "token_sem_permissao":
            self._enviar_json(403, {"erro": "Acesso proibido: Token sem privilégio de consulta a este recurso."})
            return

        # 2. Roteamento e Paginação
        if path.endswith("/arrecadacao/iptu"):
            dataset = DADOS_SIMULADOS_IPTU
        elif path.endswith("/arrecadacao/iss"):
            dataset = DADOS_SIMULADOS_ISS
        elif path.endswith("/divida-ativa/devedores"):
            dataset = DADOS_SIMULADOS_DIVIDA
        else:
            self._enviar_json(404, {"erro": f"Endpoint não encontrado: {path}"})
            return

        # Paginação: 2 registros por página para demonstrar paginação automática
        page_size = 2
        page = int(query_params.get("page", ["1"])[0])
        total_registros = len(dataset)
        total_paginas = (total_registros + page_size - 1) // page_size

        inicio = (page - 1) * page_size
        fim = inicio + page_size
        pagina_dados = dataset[inicio:fim] if inicio < total_registros else []

        payload = {
            "pagina_atual": page,
            "total_paginas": total_paginas,
            "total_registros": total_registros,
            "registros_por_pagina": page_size,
            "tem_proxima": page < total_paginas,
            "dados": pagina_dados,
        }
        self._enviar_json(200, payload)


class ServidorSimuladorSefin:
    """Controlador do servidor HTTP REST local de simulação."""

    def __init__(self, host: str = "127.0.0.1", porta: int = 8000):
        self.host = host
        self.porta = porta
        self.server = HTTPServer((self.host, self.porta), MockSefinHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def iniciar(self):
        self.thread.start()
        logger.info(
            "[SIMULAÇÃO REST ATIVA] Servidor Mock da Prefeitura de Palmas iniciado em http://%s:%d",
            self.host,
            self.porta,
        )

    def parar(self):
        self.server.shutdown()
        self.server.server_close()
        logger.info("[SIMULAÇÃO REST] Servidor Mock encerrado com sucesso.")


# ==============================================================================
# PONTO DE ENTRADA DO SCRIPT (EXECUÇÃO DIRETA)
# ==============================================================================
def main():
    """Execução principal do script de coleta."""
    print("=" * 80)
    print(" SITRIB - SISTEMA DE INTELIGÊNCIA TRIBUTÁRIA (SEFIN PALMAS-TO)")
    print(" Tarefa E1 - Sprint 3: Coleta Automatizada via API REST")
    print("=" * 80)

    # 1. Carrega variáveis de ambiente
    token = os.getenv("SEFIN_API_TOKEN")
    if not token:
        # Se não configurado, define valor de demonstração e cria alerta
        logger.warning("SEFIN_API_TOKEN não encontrado no ambiente. Utilizando token fictício de teste.")
        token = "token_ficticio_sefin_palmas_2026"
        os.environ["SEFIN_API_TOKEN"] = token

    simulacao_local = os.getenv("SEFIN_SIMULACAO_LOCAL", "true").lower() in ("true", "1", "yes")
    porta_simulacao = int(os.getenv("SEFIN_SIMULACAO_PORTA", "8000"))

    servidor_mock = None
    url_base = os.getenv("SEFIN_API_BASE_URL", "https://integracao.palmas.to.gov.br/apirest")

    if simulacao_local:
        print("\n [MODO DE SIMULAÇÃO REST ATIVADO]")
        print(" O script iniciará uma API REST HTTP local controlada com os dados municipais")
        print(" mapeados para homologação do pipeline (IPTU, ISS, Dívida Ativa).\n")
        servidor_mock = ServidorSimuladorSefin(host="127.0.0.1", porta=porta_simulacao)
        servidor_mock.iniciar()
        url_base = f"http://127.0.0.1:{porta_simulacao}"

    try:
        coletor = ColetorAPISefin(base_url=url_base, token=token, rate_limit_delay=1.0)
        arquivos = coletor.coletar_todas_categorias(diretorio_destino="data/bruto")

        print("\n" + "=" * 80)
        print(" RESULTADO DA COLETA AUTOMATIZADA:")
        print("=" * 80)
        for categoria, caminho in arquivos.items():
            print(f" -> {categoria.upper()}: {caminho}")
        print("=" * 80)
        print(" Todos os dados foram anonimizados conforme LGPD e persistidos em data/bruto/.")
        print("=" * 80 + "\n")

    finally:
        if servidor_mock:
            servidor_mock.parar()


if __name__ == "__main__":
    main()
