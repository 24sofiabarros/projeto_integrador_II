#  Documentação de Integração de API e Protocolos de Segurança (Entregável E3)

##  1. Mapeamento dos Endpoints da API REST (Sefin / Prefeitura de Palmas-TO)

O pipeline de dados consome e integra as seguintes rotas da infraestrutura pública municipal:

* **Endereço Base:** `http://integracao.palmas.to.gov.br/apirest/`
* **Endpoints Mapeados:**
  * `GET /arrecadacao/iptu`: Histórico de lançamentos e pagamentos de IPTU por exercício.
  * `GET /arrecadacao/iss`: Dados de arrecadação de ISS de empresas e autônomos.
  * `GET /divida-ativa/devedores`: Consulta de débitos inscritos em Dívida Ativa com score de cobrança.

---

##  2. Protocolos de Segurança e Proteção de Dados (LGPD)

1. **Tráfego Seguro (HTTPS/TLS 1.3):**
   * Toda a comunicação entre os scripts da aplicação e os servidores de dados deve utilizar canal criptografado HTTPS.
2. **Gestão de Credenciais e Segredos:**
   * Nenhuma chave de API ou credencial deve ser gravada em código-fonte (`hardcoded`).
   * Utilização de variáveis de ambiente via arquivo `.env` (incluído no `.gitignore`).
3. **Anonimização de Dados Sensíveis:**
   * Mascaramento preventivo de CPFs e nomes de contribuintes para relatórios públicos e testes de homologação, garantindo conformidade com a LGPD.

---

##  3. Mecanismo de Autenticação: Descrição Detalhada da Autenticação na API

### 3.1. Identificação do Mecanismo
Conforme a modelagem arquitetural do sistema (`IntegradorAPIsExternas.token_autenticacao` definida em `docs/diagrama_classes.md`) e os requisitos de ingestão de dados governamentais (**RF02**), a integração com a API REST da Secretaria Municipal de Finanças (Sefin / Prefeitura de Palmas-TO) adota o mecanismo de **Token de Autenticação via Cabeçalho HTTP (Bearer Token)**.

* **Tipo de Mecanismo:** Autenticação baseada em token institucional (*Bearer Token / API Key*).
* **Protocolo de Transporte:** HTTPS (TLS 1.3 obrigatório para proteção de dados em trânsito).
* **Cabeçalho Utilizado:** `Authorization: Bearer <SEFIN_API_TOKEN>`

> **Nota de conformidade:**  
> No estágio atual da Sprint 2, a arquitetura de dados e persistência 3FN encontram-se implementadas (`src/banco/` e `src/estruturas/arquitetura_dados.py`), enquanto a camada de integração HTTP está estruturada conceitualmente no diagrama de classes e nas especificações de requisitos, orientando os padrões de segurança aqui documentados sem implementação de código adicional nesta etapa.

### 3.2. Fluxo de Autenticação
1. **Emissão e Obtenção do Token:** O token de acesso institucional é gerado e homologado pela Secretaria Municipal de Finanças (Sefin / Prefeitura de Palmas) mediante termo de convênio e credenciamento institucional do SITRIB, definindo escopos de leitura para arrecadação (IPTU, ISS) e Dívida Ativa.
2. **Carregamento Local:** A aplicação lê o token em tempo de execução a partir do arquivo de ambiente local (`.env`), sem expô-lo no código-fonte.
3. **Envio da Requisição:** O cliente HTTP anexa o token ao cabeçalho `Authorization` da requisição HTTP `GET`.
4. **Validação no Servidor:** O gateway/API municipal valida a assinatura, expiração e permissões associadas ao token. Havendo conformidade, a resposta HTTP `200 OK` é retornada com a carga de dados em formato JSON.

### 3.3. Armazenamento e Proteção de Credenciais
* **Variáveis de Ambiente:** O token é armazenado exclusivamente no arquivo `.env` no ambiente de execução sob a chave `SEFIN_API_TOKEN`.
* **Proteção no Controle de Versão:** O arquivo `.env` e suas variações (`.env.*`) estão expressamente configurados no arquivo `.gitignore` do repositório, impedindo commit acidental.
* **Arquivo de Exemplo:** Um modelo `.env.example` sem valores reais deve ser utilizado pela equipe como referência de configuração.
* **Isolamento em Memória:** No ambiente Python, a credencial é acessada dinamicamente via `os.getenv("SEFIN_API_TOKEN")` apenas no momento da instanciação da camada integradora, não sendo persistida em disco nem exposta em artefatos públicos.

### 3.4. Comportamento em Caso de Falha de Autenticação
Em alinhamento com os critérios de aceite do requisito **RF02**:
* **HTTP 401 Unauthorized:** Retornado caso o token seja inválido, esteja expirado ou tenha sido omitido. O pipeline interrompe imediatamente a execução da rota correspondente e registra a falha no log de auditoria com nível `ERROR`. Não há disparo de retentativas automáticas quando o código retornado for 401, evitando bloqueios por força bruta.
* **HTTP 403 Forbidden:** Retornado caso o token seja válido, mas não possua privilégios para o endpoint específico consultado (ex.: ausência de permissão para visualização de devedores da Dívida Ativa). A requisição é abortada e a divergência de permissão é sinalizada.
* **Tratamento Seguro:** Nenhuma informação de credencial ou chave é impressa nos logs de erro (`TrilhaAuditoria`), garantindo conformidade com a LGPD e evitando vazamento acidental em arquivos de rastreio.

### 3.5. Cuidados de Segurança
* **Proibição de Hardcoding:** É estritamente vedada a inserção de chaves ou tokens literais nos arquivos `.py`, scripts SQL ou documentações.
* **Princípio do Menor Privilégio:** O token concedido deve possuir apenas permissões de leitura (`GET`) necessárias aos endpoints mapeados (`/arrecadacao/iptu`, `/arrecadacao/iss`, `/divida-ativa/devedores`).
* **Sanitização de Logs:** Cabeçalhos `Authorization` devem ser explicitamente mascarados ou expurgados em saídas de console e relatórios de auditoria.
* **Rotação e Revogação:** Procedimento operacional de suporte à substituição do token mediante atualização da variável de ambiente no servidor sem necessidade de alteração de código.

### 3.6. Exemplo Fictício e Seguro de Requisição

#### Exemplo em cURL:
```bash
curl -X GET "https://integracao.palmas.to.gov.br/apirest/arrecadacao/iptu?exercicio=2024" \
     -H "Authorization: Bearer EXEMPLO_TOKEN_FICTICIO_SEFIN_PALMAS_2026" \
     -H "Accept: application/json"
```

#### Exemplo Conceitual em Python:
```python
import os
import requests

def consultar_dados_api(endpoint: str) -> dict:
    url_base = "https://integracao.palmas.to.gov.br/apirest"
    token = os.getenv("SEFIN_API_TOKEN")

    if not token:
        raise ValueError("Variável de ambiente SEFIN_API_TOKEN não configurada.")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    response = requests.get(f"{url_base}{endpoint}", headers=headers, timeout=10)

    if response.status_code == 401:
        # Tratamento de autenticação inválida
        raise PermissionError("Falha de autenticação na API Sefin: Token inválido ou expirado (HTTP 401).")
    elif response.status_code == 403:
        # Tratamento de autorização insuficiente
        raise PermissionError("Acesso negado: Token sem permissão para este endpoint (HTTP 403).")

    response.raise_for_status()
    return response.json()
```