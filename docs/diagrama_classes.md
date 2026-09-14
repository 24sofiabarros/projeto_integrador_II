# Diagrama de Classes - Sistema SITRIB

Este documento apresenta a modelagem orientada a objetos das entidades centrais do **SITRIB (Sistema Integrado de Gestão Tributária)**, refletindo a arquitetura em camadas (MVC) e as regras de negócio especificadas nos Requisitos Funcionais (RF01 a RF10).

---

## 1. Diagrama de Classes (Mermaid)

```mermaid
classDiagram
    direction TB

    %% ==========================================
    %% CLASSES BASE E CONTROLE DE ACESSO
    %% ==========================================
    class Usuario {
        <<abstract>>
        +String id_usuario
        +String login
        +String senha_hash
        +String email
        +PapelUsuario papel
        +Boolean ativo
        +autenticar(String login, String senha) Boolean
        +validarMFA(String token) Boolean
    }

    class AuditorFiscal {
        +String matricula_funcional
        +String departamento
        +analisarAlerta(AlertaInconsistencia alerta) void
        +emitirNotificacao(DebitoTributario debito) NotificacaoFiscal
        +abrirProcessoFiscal(Contribuinte contribuinte) void
    }

    class GestorFazendario {
        +String cargo
        +visualizarDashboardKPIs() Object
        +executarSimulador(SimuladorCenarioFiscal cenario) Object
        +aprovarPoliticaFiscal(String diretriz) void
    }

    class Contribuinte {
        +String cpf_cnpj
        +String nome
        +String email
        +String telefone
        +Boolean possui_iptu_social
        +consultarDebitos() List~DebitoTributario~
        +emitirGuiaDAM(DebitoTributario debito) GuiaDAM
        +solicitarRevisaoCadastral(String motivo) String
    }

    %% ==========================================
    %% CADASTRO E TRIBUTAÇÃO
    %% ==========================================
    class Imovel {
        +String inscricao_imobiliaria
        +String cpf_cnpj_proprietario
        +String logradouro
        +String bairro
        +String cep
        +String zona_fiscal
        +Float area_terreno
        +Float area_construida
        +Float valor_venal
        +consultarDadosImobiliarios() Object
    }

    class DebitoTributario {
        <<abstract>>
        +int id_debito
        +String cpf_contribuinte
        +Float valor_original
        +Float valor_juros
        +Float valor_multa
        +int ano_exercicio
        +Date data_vencimento
        +StatusDebito status
        +calcularValorTotal() Float
        +atualizarStatus(StatusDebito novo_status) void
    }

    class DebitoIPTU {
        +String inscricao_imobiliaria
        +Float score_inadimplencia
        +Boolean isencao_social
        +calcularScoreIA() Float
        +aplicarRegraIPTUSocial() Boolean
    }

    class DebitoISS {
        +String inscricao_municipal
        +String competencia
        +Float valor_declarado
        +Float valor_apurado_nfse
        +Float divergencia_detectada
        +conciliarDivergencia() Boolean
    }

    %% ==========================================
    %% FISCALIZAÇÃO, ALERTAS E COBRANÇA
    %% ==========================================
    class AlertaInconsistencia {
        +int id_alerta
        +String cpf_cnpj_alvo
        +String tipologia
        +Float valor_estimado_divergencia
        +GrauCriticidade criticidade
        +StatusAlerta status
        +DateTime data_identificacao
        +String justificativa_encerramento
        +atualizarStatus(StatusAlerta novo_status, String justificativa) void
    }

    class NotificacaoFiscal {
        +int id_notificacao
        +String numero_processo
        +DateTime data_emissao
        +Date prazo_defesa
        +String chave_autenticacao
        +String qrcode_validacao
        +gerarDocumentoPDF() Byte[]
        +enviarNotificacao(String canal) Boolean
    }

    class GuiaDAM {
        +int id_guia
        +String codigo_barras
        +String chave_pix_copia_cola
        +Date data_vencimento
        +Float valor_cobrado
        +Boolean liquidado
        +gerarCobrancaPix() String
        +confirmarPagamento() void
    }

    %% ==========================================
    %% AUDITORIA, SIMULAÇÃO E INTEGRAÇÃO
    %% ==========================================
    class TrilhaAuditoria {
        +int id_log
        +String id_usuario
        +String endereco_ip
        +DateTime data_hora
        +String acao_executada
        +String entidade_afetada
        +String dados_anteriores
        +String dados_novos
        +registrarOperacao() void
    }

    class IntegradorAPIsExternas {
        +String endpoint_base
        +String token_autenticacao
        +int timeout_segundos
        +sincronizarReceitaFederal(String cnpj) Object
        +sincronizarDetranTO(String cpf_cnpj) Object
        +sincronizarCartorioImoveis(String matricula) Object
    }

    class SimuladorCenarioFiscal {
        +int id_simulacao
        +int exercicio_referencia
        +String tributo_alvo
        +Float percentual_desconto
        +Float adesao_estimada
        +Float projecao_arrecadacao
        +calcularImpactoOrcamentario() Object
        +exportarRelatorio(String formato) Byte[]
    }

    %% ==========================================
    %% ENUMERAÇÕES
    %% ==========================================
    class PapelUsuario {
        <<enumeration>>
        GESTOR_FAZENDARIO
        AUDITOR_FISCAL
        CIDADAO_CONTRIBUINTE
    }

    class StatusDebito {
        <<enumeration>>
        ABERTO
        QUITADO
        PARCELADO
        DIVIDA_ATIVA
        ISENTO
    }

    class StatusAlerta {
        <<enumeration>>
        PENDENTE
        EM_APURACAO
        PROCEDENTE
        DESCARTADO
    }

    class GrauCriticidade {
        <<enumeration>>
        BAIXA
        MEDIA
        ALTA
    }

    %% ==========================================
    %% RELAÇÕES E CARDINALIDADES
    %% ==========================================
    %% Herança (Generalização)
    Usuario <|-- AuditorFiscal
    Usuario <|-- GestorFazendario
    Usuario <|-- Contribuinte
    DebitoTributario <|-- DebitoIPTU
    DebitoTributario <|-- DebitoISS

    %% Agregações / Tipagens de Enums
    Usuario o-- PapelUsuario
    DebitoTributario o-- StatusDebito
    AlertaInconsistencia o-- StatusAlerta
    AlertaInconsistencia o-- GrauCriticidade

    %% Associações de Domínio
    Contribuinte "1" --> "0..*" Imovel : possui
    Contribuinte "1" --> "0..*" DebitoTributario : vinculado_a
    Imovel "1" --> "0..*" DebitoIPTU : incide_sobre
    DebitoTributario "1" --> "0..*" GuiaDAM : gera
    DebitoTributario "1" --> "0..*" NotificacaoFiscal : motiva

    AuditorFiscal "1" --> "0..*" AlertaInconsistencia : analisa
    AuditorFiscal "1" --> "0..*" NotificacaoFiscal : emite
    GestorFazendario "1" --> "0..*" SimuladorCenarioFiscal : opera

    %% Dependências de Integração e Auditoria
    IntegradorAPIsExternas ..> Contribuinte : enriquece_dados
    IntegradorAPIsExternas ..> Imovel : sincroniza_cadastro
    AlertaInconsistencia ..> Contribuinte : referencia
    TrilhaAuditoria ..> Usuario : audita_acoes
```

---

## 2. Descrição das Entidades Principais

### A) Núcleo de Usuários e Acesso (RBAC - RF01)
* **`Usuario`**: Classe base/abstrata que reúne as credenciais de autenticação, e-mail institucional, controle de status e validação de duplo fator (MFA / Gov.br).
* **`AuditorFiscal`**: Subclasse com atribuições de correição e fiscalização: análise de alertas fiscais, cruzamento de declarações com notas fiscais e emissão de intimações.
* **`GestorFazendario`**: Subclasse voltada à gestão estratégica: visualização de indicadores do painel executivo (KPIs) e realização de simulações orçamentárias.
* **`Contribuinte`**: Subclasse associada a munícipes e pessoas jurídicas: permite consulta integrada de situação fiscal, solicitação de revisões cadastrais e emissão de guias DAM com PIX.

### B) Núcleo Tributário e Imobiliário (RF06 e RF08)
* **`Imovel`**: Modela a unidade física e territorial cadastrada no município de Palmas, vinculando dados como zona fiscal, área e valor venal para apuração de IPTU.
* **`DebitoTributario`**: Classe abstrata comum a todas as dívidas tributárias municipais, padronizando o cômputo de juros, multas, prazos de vencimento e ciclo de vida do débito.
* **`DebitoIPTU`**: Especialização para débitos prediais/territoriais urbanos, incorporando o `score_inadimplencia` gerado pelo módulo preditivo de IA e as diretrizes de isenção do **IPTU Social**.
* **`DebitoISS`**: Especialização para o imposto sobre serviços, agregando conciliação entre o faturamento mensal declarado e as notas fiscais emitidas (NFS-e).

### C) Fiscalização, Cobrança e Arrecadação (RF03, RF04 e RF07)
* **`AlertaInconsistencia`**: Instanciada pelo motor de cruzamento de dados quando há incongruências patrimoniais, desvios de ISS ou indícios de sonegação, com níveis de criticidade (Baixa, Média, Alta).
* **`NotificacaoFiscal`**: Documento oficial expedido ao contribuinte com número de processo administrativo, QR Code de validação pública e chave criptográfica.
* **`GuiaDAM`**: Documento de Arrecadação Municipal que consolida débitos para pagamento, suportando código de barras FEBRABAN e chave dinâmica PIX (copia e cola).

### D) Governança, Integrações e Auditoria (RF02, RF05, RF09 e RF10)
* **`IntegradorAPIsExternas`**: Camada de serviço desacoplada para comunicação síncrona/assíncrona com Receita Federal, Detran-TO e Cartórios de Imóveis.
* **`SimuladorCenarioFiscal`**: Módulo preditivo para análise de impacto fiscal diante de variações de alíquotas ou programas de regularização (REFIS).
* **`TrilhaAuditoria`**: Entidade de registro imutável para todas as operações sensíveis no sistema, garantindo conformidade rigorosa com a LGPD.
