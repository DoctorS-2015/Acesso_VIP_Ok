# Sistema de Controle de Acesso a Eventos

## Visão Geral do Projeto

Este projeto é um sistema web robusto e completo desenvolvido para gerenciar e controlar o acesso a eventos de forma eficiente e segura. A aplicação oferece uma interface intuitiva para validação de acesso para participantes e um painel administrativo completo para a gestão de eventos, usuários e relatórios detalhados. O sistema foi concebido para ser flexível e adaptável a diferentes cenários de eventos, desde pequenas reuniões até grandes festivais, garantindo a integridade dos dados e a segurança das informações.

## Tecnologias Utilizadas

### Backend

- **Python:** Linguagem de programação principal.
- **Flask:** Micro-framework web para construção da API e lógica de negócio.
- **Flask-SQLAlchemy:** Extensão do Flask para integração com SQLAlchemy, um ORM (Object-Relational Mapper) para interação com bancos de dados relacionais.
- **Flask-JWT-Extended:** Extensão para gerenciamento de autenticação baseada em JSON Web Tokens (JWT).
- **Werkzeug Security:** Utilizado para hashing seguro de senhas.
- **PyMySQL:** Driver para conexão com bancos de dados MySQL/MariaDB.
- **python-dotenv:** Para gerenciamento de variáveis de ambiente.

### Frontend

- **HTML5:** Estrutura das páginas web.
- **Tailwind CSS:** Framework CSS utility-first para estilização rápida e responsiva.
- **JavaScript (Vanilla JS):** Para interatividade do lado do cliente, validações de formulário e manipulação do DOM.
- **Font Awesome:** Biblioteca de ícones para enriquecer a interface do usuário.

### Banco de Dados

- **MariaDB/MySQL:** Sistema de gerenciamento de banco de dados relacional (SGBD).

## Funcionalidades

### Módulo de Validação de Acesso (Público)

- **Formulário de Validação:** Interface intuitiva para que os participantes insiram seus dados (Nome, Ingresso, CPF) para validação de acesso.
- **Lógica de Acesso Flexível:** O sistema permite configurar regras de acesso baseadas em listas VIP e códigos de ingresso válidos.
- **Validação de CPF:** Implementação de um algoritmo robusto para validação de CPFs brasileiros, garantindo a integridade dos dados de entrada.
- **Feedback em Tempo Real:** Mensagens claras de 


liberação ou negação de acesso são exibidas ao usuário.

### Módulo Administrativo

- **Autenticação Segura:** Acesso restrito a administradores via login com usuário e senha, protegido por JWT e cookies HTTPOnly.
- **Gestão de Eventos (CRUD):**
    - **Criação de Eventos:** Interface para cadastrar novos eventos com nome, datas de início e fim, local e descrição.
    - **Visualização de Eventos:** Listagem clara de todos os eventos, com status (Ativo, Próximo, Finalizado) e detalhes.
    - **Edição de Eventos:** Funcionalidade para atualizar informações de eventos existentes.
    - **Exclusão de Eventos:** Opção para remover eventos, com confirmação para evitar exclusões acidentais.
- **Relatórios de Acesso:**
    - **Visão Geral:** Dashboard com estatísticas de acessos totais, liberados e negados.
    - **Filtros:** Possibilidade de filtrar relatórios por status de acesso.
    - **Exportação CSV:** Funcionalidade para exportar todos os dados de acesso para um arquivo CSV, facilitando a análise externa.
- **Gerenciamento de Acessos:** Embora não totalmente implementado no `app.py` para VIPs e Ingressos de forma dinâmica, a estrutura do banco de dados e a interface no `controle.html` indicam a intenção de gerenciar VIPs e ingressos por evento, o que é uma funcionalidade crucial para um sistema de controle de acesso.

## Arquitetura do Sistema

### Backend

O backend é construído com Flask, seguindo uma arquitetura MVC (Model-View-Controller) simplificada, onde:

- **Modelos (Models):** Definidos via SQLAlchemy ORM (`Acesso`, `User`, `Evento`), representam as tabelas do banco de dados e encapsulam a lógica de negócio relacionada aos dados.
- **Views (Templates):** Arquivos HTML renderizados pelo Jinja2, que recebem dados do backend para exibir a interface do usuário.
- **Controladores (Controllers/Rotas):** As funções de rota no `app.py` atuam como controladores, processando requisições HTTP, interagindo com os modelos e renderizando as views apropriadas.

Um ponto de destaque é a função `get_acessos_column_map()`, que adiciona uma camada de abstração ao acesso ao banco de dados. Esta função permite que o sistema se adapte a diferentes convenções de nomenclatura de colunas na tabela `acessos`, tornando-o mais robusto e menos propenso a quebras em ambientes com esquemas de banco de dados ligeiramente diferentes. Isso é alcançado através da inspeção do `INFORMATION_SCHEMA` (para MySQL/PostgreSQL) ou `PRAGMA table_info` (para SQLite), ou por um fallback que extrai os nomes das colunas de uma query de seleção. Essa abordagem demonstra um design preocupado com a flexibilidade e a compatibilidade.

### Frontend

O frontend é composto por páginas HTML estáticas que são dinamicamente preenchidas e interagem com o usuário através de JavaScript. A estilização é feita com Tailwind CSS, que permite um desenvolvimento ágil e um design consistente. A estrutura do frontend é modular, com arquivos `.html`, `.css` e `.js` separados, facilitando a manutenção e a escalabilidade.

- **`index.html`:** Página principal de validação de acesso, com um formulário multi-etapas e feedback visual.
- **`login.html`:** Página de autenticação para administradores.
- **`controle.html`:** Painel de controle administrativo para gestão de eventos, com estatísticas e opções de gerenciamento.
- **`criar_evento.html`:** Formulário para criação/edição de eventos.
- **`relatorio.html`:** Página de visualização de relatórios de acesso.
- **`custom.css`:** Contém estilos personalizados e importações de fontes/ícones.
- **`main.js` e `validation.js`:** Arquivos JavaScript para lógica de interação, validação de formulário e manipulação do DOM.

## Estrutura do Banco de Dados

O banco de dados `acesso_vip_db` é composto pelas seguintes tabelas:

- **`users`:** Armazena informações dos usuários administradores (`id`, `username`, `password_hash`, `is_admin`). A senha é armazenada como um hash seguro.
- **`eventos`:** Contém os detalhes dos eventos (`id`, `nome`, `data_inicio`, `data_fim`, `local`, `descricao`).
- **`acessos`:** Registra cada tentativa de acesso (`id`, `nome_acesso`, `cpf_acesso`, `data_hora`, `status_acesso`, `motivo_negado`, `evento_id`, `ingresso_id`, `vip_id`). Possui chaves estrangeiras para `eventos`, `ingressos` e `vips`.
- **`ingressos`:** Gerencia os ingressos válidos para os eventos (`id`, `codigo`, `tipo`, `valor`, `utilizado`, `evento_id`).
- **`vips`:** Armazena a lista de convidados VIP (`id`, `nome_completo`, `cpf`, `evento_id`).

As relações entre as tabelas são estabelecidas por chaves estrangeiras, garantindo a integridade referencial e a consistência dos dados. Por exemplo, um registro de `acesso` está diretamente ligado a um `evento`, e opcionalmente a um `ingresso` ou `vip`.

## Como Rodar o Projeto

### Pré-requisitos

- Python 3.x
- pip (gerenciador de pacotes Python)
- Um servidor de banco de dados MariaDB ou MySQL (ou SQLite para desenvolvimento local)

### Configuração

1.  **Clone o repositório:**
    ```bash
    git clone <URL_DO_SEU_REPOSITORIO>
    cd <nome_do_repositorio>
    ```

2.  **Crie um ambiente virtual (recomendado):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure o banco de dados:**
    - Crie um banco de dados chamado `acesso_vip_db` no seu servidor MariaDB/MySQL.
    - Importe o esquema e os dados iniciais usando o arquivo `acesso_vip_db.sql`:
      ```bash
      mysql -u seu_usuario -p acesso_vip_db < acesso_vip_db.sql
      ```
      (Substitua `seu_usuario` pelo seu usuário do MySQL/MariaDB e digite sua senha quando solicitado.)
    - Alternativamente, para SQLite (desenvolvimento/teste), o Flask-SQLAlchemy criará o arquivo `fallback.db` automaticamente.

5.  **Crie um arquivo `.env` na raiz do projeto** com as seguintes variáveis de ambiente:
    ```
    SECRET_KEY='sua_chave_secreta_aqui' # Uma string longa e aleatória
    JWT_SECRET_KEY='sua_chave_jwt_secreta_aqui' # Outra string longa e aleatória
    DATABASE_URL='mysql+pymysql://seu_usuario:sua_senha@seu_host:3306/acesso_vip_db'
    ```
    - Substitua `seu_usuario`, `sua_senha` e `seu_host` pelas credenciais do seu banco de dados. Para SQLite, você pode omitir `DATABASE_URL` ou defini-lo como `sqlite:///fallback.db`.

### Execução

1.  **Execute a aplicação Flask:**
    ```bash
    python app.py
    ```

2.  **Acesse a aplicação:**
    Abra seu navegador e acesse `http://127.0.0.1:5000/` para a página de validação de acesso.
    Para o painel administrativo, acesse `http://127.0.0.1:5000/login`.

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou pull requests para melhorias, correções de bugs ou novas funcionalidades.

## Autor

Ramiriz Nóbrega



