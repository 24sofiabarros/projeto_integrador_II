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