Projeto Integrador (PI) - Sprint 1

1. Orientações Gerais da Atividade
Esta atividade tem como objetivo consolidar os conceitos trabalhados em sala de aula
(Metodologias Ágeis/Scrum, Engenharia de Requisitos, Git e Estruturação de Projetos),
aplicando-os diretamente ao Projeto Integrador do semestre. Os grupos (compostos por 5
integrantes) devem estruturar a base do projeto, estabelecer os papéis de liderança técnica e
de negócio, mapear os requisitos com critérios de aceitação e comprovar a colaboração
individual no controle de versão.

1.1. Itens Obrigatórios de Entrega

● Repositório no GitHub: Criação de repositório da equipe com estrutura inicial de
diretórios para projeto em Python (ex.: pasta de código-fonte src/, pasta de
documentação docs/, arquivo .gitignore para Python e arquivo de dependências
requirements.txt ou pyproject.toml).

● Comprovação de Participação Individual (Git): Todos os 5 membros devem ser
colaboradores do repositório e possuir histórico de contribuições registrado (commits).
Deve ser anexado um print/captura de tela da aba Insights > Contributors ou do
histórico de Commits do repositório, evidenciando o autor e a mensagem de commit de
cada estudante.

● Definição e Justificativa de Papéis: Designação do Product Owner (PO) e do Scrum
Master (SM), acompanhada da fundamentação teórica de suas atribuições.

● Mapeamento de Requisitos Funcionais: Especificação de no mínimo 10 Requisitos
Funcionais (RF) estruturados com seus respectivos Critérios de Aceite testáveis.

● Requisitos Não Funcionais: Mapeamento de 3 a 5 Requisitos Não Funcionais (RNF)
voltados a restrições de tecnologia, usabilidade e portabilidade.

● Matriz de Priorização MoSCoW: Classificação de todo o escopo levantado nas
categorias Must Have, Should Have, Could Have e Won't Have.

● Modelagem UML (Opcional): Inclusão de diagramas (Casos de Uso, Classes ou
Sequência) na pasta docs/ como documentação de apoio.

2. Roteiro e Template de Preenchimento da Equipe

(A equipe deve transcrever e preencher as seções a seguir diretamente no README.md do
repositório ou em documento estruturado dentro da pasta /docs).

2.1. Identificação da Equipe e Links

Nome do Integrante Matrícula Usuário GitHub (@) Papel Principal no Time

[Nome Completo 1] [Matrícula] @usuario1 Product Owner (PO)
[Nome Completo 2] [Matrícula] @usuario2 Scrum Master (SM)
[Nome Completo 3] [Matrícula] @usuario3 Desenvolvedor / Equipe
Técnica
[Nome Completo 4] [Matrícula] @usuario4 Desenvolvedor / Equipe
Técnica
[Nome Completo 5] [Matrícula] @usuario5 Desenvolvedor / Equipe
Técnica

Link do Repositório GitHub: https://github.com/usuario/nome-do-repositorio

2.2. Fundamentação e Dinâmica dos Papéis Ágeis

A) Product Owner (PO)
1. Quem é o Product Owner da equipe?
2. Quais são as principais atribuições e responsabilidades do PO perante o Projeto Integrador?
(Ex.: domínio das regras de negócio, interface com o cliente/professor, priorização contínua do
Backlog e validação das entregas segundo os critérios de aceite).
3.Como o PO validará se as funcionalidades entregues pelos desenvolvedores realmente
cumprem o propósito do projeto?

B) Scrum Master (SM)
1. Quem é o Scrum Master da equipe?
2. Quais são as responsabilidades do Scrum Master na condução do time?
3. Qual será o canal de comunicação oficial da equipe e a frequência dos alinhamentos
semanais?

2.3. Especificação de Requisitos Funcionais (RF)

Apresente no mínimo 5 requisitos funcionais do sistema. Cada requisito deve ter uma
descrição clara (ou formato de História de Usuário) e critérios de aceite objetivos e testáveis.

ID Nome do Requisito Descrição / História de Usuário Critérios de Aceite
(Validação)

RF01 Cadastro de Usuário O sistema deve permitir o registro de
novos usuários com e-mail, nome e senha.
1. E-mail deve ser validado e
único.
2. Senha deve possuir tamanho
mínimo.
3. Retornar mensagem clara de
confirmação.

RF02 Autenticação no Sistema O sistema deve autenticar usuários
registrados via credenciais válidas.
1. Credenciais corretas liberam
a sessão.
2. Credenciais inválidas alertam
o usuário.

RF5 [Nome RF5] [Descrição detalhada] [Regras para considerar pronto]

2.4. Requisitos Não Funcionais (RNF)

Especifique de 3 a 5 requisitos não funcionais aplicáveis ao projeto (tecnologia, interface, portabilidade ou boas práticas).
ID Categoria Descrição da Restrição Métrica / Forma de Teste

RNF01 Tecnologia / Backend O sistema deve ser desenvolvido
obrigatoriamente utilizando a linguagem
Python Compatível com Python 3.12+.

RNF02 Portabilidade As dependências devem estar isoladas e
descritas em arquivo de manifesto de
pacotes.
Instalação com comando padrão via requirements.txt.

RNF03 Usabilidade O sistema deve fornecer mensagens claras
de sucesso ou erro para todas as ações do
usuário.
Feedback visual/textual imediato em todas as operações.

RNF04 Documentação O README.md deve conter instruções
completas de instalação, configuração e
Reproducibilidade do setup por terceiros sem

ID Categoria Descrição da Restrição Métrica / Forma de Teste
execução. erros.

2.5. Matriz de Priorização MoSCoW

Classifique os requisitos funcionais e não funcionais em suas respectivas categorias de
prioridade para a primeira iteração do semestre:

● Must Have (Indispensável para o MVP): [Listar IDs dos requisitos fundamentais, ex.:
RF01, RF02, RNF01]
● Should Have (Importante, alta prioridade): [Listar IDs dos requisitos de alto valor, ex.:
RF03, RF05, RNF03]
● Could Have (Desejável, se houver tempo hábil): [Listar IDs de melhorias secundárias,
ex.: RF08, RNF04]
● Won't Have (Fora do escopo desta entrega): [Listar IDs de funcionalidades
descartadas/adiadas para versões futuras]

2.6. Comprovação de Contribuições no Git

Para garantir que todos os 5 integrantes colaboraram ativamente e utilizaram o versionamento
de código, a equipe deve incluir nesta seção (ou anexar como imagem na pasta docs/ e exibir
no README):

1. Print do Painel de Contribuidores: Captura de tela da página do repositório em Insights
> Contributors (ou Network), demonstrando o nome/login dos 5 integrantes com seus
respectivos commits.

2. Print do Histórico de Commits: Captura de tela da listagem de commits do branch
principal (main), exibindo a mensagem descritiva e o autor de cada alteração.

2.7. Documentação Complementar e Modelagem UML (Opcional)

Espaço destinado a equipes que queiram adicionar os diagramas UML desenvolvidos em aula 
(Casos de Uso, Classes e/ou Sequência). Imagens ou links para os arquivos dentro de docs/
podem ser inseridos aqui para bonificação na avaliação.

3. Rubrica de Avaliação da Atividade
4. 
Critério Descrição do Atendimento Peso
Engenharia de
Requisitos Definição clara de pelo menos 10 RFs com critérios de
aceite testáveis e 3 a 5 RNFs consistentes. 35%
Papéis Ágeis e
Priorização
Definição justificada de PO e SM e aplicação correta
da matriz MoSCoW.
25%
Repositório e
Estrutura Inicial
Repositório bem estruturado com pastas Python,
README completo e organização limpa.
20%
Colaboração Git
(Prints)
Comprovação de contribuição individual de todos os 5
integrantes via histórico de commits.
20%
Bônus: Modelagem
UML
Inclusão coerente de diagramas de Casos de Uso,
Classes ou Sequência na documentação.
+ 10% (Extra)










































