# app.py
"""
Aplicação Flask para controle de acesso a eventos.

Funcionalidades:
- Validação de acesso por formulário (Nome, Ingresso, CPF).
- Autenticação de administradores via JWT (JSON Web Tokens) armazenados em cookies.
- Painel de administrador para visualização de relatórios de acesso.
- Funcionalidades de CRUD (Criar, Ler, Apagar) para eventos.
- Exportação de relatórios para o formato CSV.
- Lógica de banco de dados adaptável para diferentes nomes de colunas na tabela 'acessos'.
"""
from flask import Flask, render_template, request, redirect, url_for, session, Response, make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from dotenv import load_dotenv
import os
import re
from datetime import datetime, timedelta
from io import StringIO
import csv

from werkzeug.security import generate_password_hash, check_password_hash

# Módulos para gerenciamento de autenticação com JSON Web Tokens.
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required,
    get_jwt_identity, set_access_cookies, unset_jwt_cookies,
    verify_jwt_in_request
)
from flask_jwt_extended.exceptions import NoAuthorizationError

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'chave_fallback_seguranca')

# --- Configurações da Aplicação ---

# Configuração do Banco de Dados: utiliza a DATABASE_URL do .env ou um fallback SQLite.
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 'sqlite:///fallback.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuração do JWT (JSON Web Token)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt_fallback_seguranca')
app.config['JWT_TOKEN_LOCATION'] = ['cookies']  # Define que o token será enviado via cookies.
app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
# ATENÇÃO: Desabilitado em DEV. Habilitar em produção para proteção contra CSRF.
app.config['JWT_COOKIE_CSRF_PROTECT'] = False
# ATENÇÃO: Defina como True em produção (HTTPS) para que o cookie só seja enviado em conexões seguras.
app.config['JWT_COOKIE_SECURE'] = False
app.config['JWT_COOKIE_SAMESITE'] = 'Lax'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

db = SQLAlchemy(app)
jwt = JWTManager(app)


# --- Handlers Globais ---

@jwt.unauthorized_loader
def unauthorized_callback(callback):
    """
    Handler global para requisições não autorizadas.

    Quando uma rota protegida por @jwt_required() é acessada sem um token JWT
    válido, em vez de retornar um erro JSON, esta função redireciona o
    usuário para a página de login.
    """
    return redirect(url_for('login'))


# --- Modelos de Banco de Dados (SQLAlchemy ORM) ---

class Acesso(db.Model):
    """Mapeia a tabela 'acessos' que armazena os registros de entrada."""
    __tablename__ = 'acessos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255))
    ingresso = db.Column(db.String(100))
    cpf = db.Column(db.String(20))
    data = db.Column(db.String(50))
    status = db.Column(db.String(50))


class User(db.Model):
    """Mapeia a tabela 'users' para autenticação de administradores."""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Integer, nullable=True) # 1 para admin, 0 ou NULL para não admin


class Evento(db.Model):
    """Mapeia a tabela 'eventos' para gerenciamento de eventos."""
    __tablename__ = 'eventos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    data_inicio = db.Column(db.DateTime, nullable=False)
    data_fim = db.Column(db.DateTime, nullable=False)
    local = db.Column(db.String(255))
    descricao = db.Column(db.Text)


# --- Funções Utilitárias ---

def validar_cpf(cpf):
    """
    Valida um número de CPF brasileiro.

    Args:
        cpf (str): O CPF a ser validado, podendo conter ou não pontuação.

    Returns:
        bool: True se o CPF for válido, False caso contrário.
    """
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    soma1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    dig1 = (soma1 * 10 % 11) % 10
    soma2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    dig2 = (soma2 * 10 % 11) % 10
    return cpf[-2:] == f"{dig1}{dig2}"


def get_acessos_column_map():
    """
    Mapeia dinamicamente os nomes das colunas da tabela 'acessos'.

    Esta função inspeciona o banco de dados para encontrar os nomes reais das
    colunas (ex: 'nome', 'nome_acesso', 'name'), permitindo que a aplicação
    funcione com diferentes esquemas de banco de dados sem alteração no código.

    Returns:
        dict: Um dicionário mapeando nomes lógicos (ex: 'nome') para os
              nomes de coluna encontrados no banco de dados (ex: 'nome_acesso').
    """
    col_map = {
        'nome': None, 'cpf': None, 'data': None,
        'status': None, 'motivo': None
    }
    try:
        # Tenta obter o esquema via metadados (padrão para MySQL/PostgreSQL)
        sql = text("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = 'acessos'
        """)
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        if db_url.startswith('sqlite'):
            insp = db.engine.execute(text("PRAGMA table_info(acessos)"))
            cols = [row[1] for row in insp.fetchall()]
        else:
            schema = db_url.rsplit('/', 1)[-1].split('?')[0]
            cols = [row[0] for row in db.session.execute(sql, {'schema': schema}).fetchall()]
    except Exception:
        # Fallback: executa uma query e extrai os nomes das colunas do resultado.
        try:
            insp = db.engine.execute(text("SELECT * FROM acessos LIMIT 1"))
            cols = [c for c in insp.keys()]
        except Exception:
            cols = []

    normalized = [c.lower() for c in cols]
    for c in normalized:
        if c in ('nome', 'nome_acesso', 'name'):
            if not col_map['nome']: col_map['nome'] = c
        if c in ('cpf', 'cpf_acesso'):
            if not col_map['cpf']: col_map['cpf'] = c
        if c in ('data', 'data_hora', 'datahora', 'created_at'):
            if not col_map['data']: col_map['data'] = c
        if c in ('status', 'status_acesso'):
            if not col_map['status']: col_map['status'] = c
        if c in ('motivo', 'motivo_negado', 'reason'):
            if not col_map['motivo']: col_map['motivo'] = c

    # Tenta um mapeamento final por substring, caso as correspondências exatas falhem.
    for key in col_map:
        if col_map[key] is None and len(normalized) > 0:
            for cand in normalized:
                if key in cand:
                    col_map[key] = cand
                    break
    return col_map


# --- Rotas Públicas ---

@app.route('/', methods=['GET', 'POST'])
def index():
    """Página inicial para registro e validação de acesso."""
    resultado = None
    acesso = None
    p = q = r = False

    if request.method == 'POST':
        nome = request.form['nome']
        ingresso = request.form['ingresso']
        cpf = request.form['cpf']
        evento_id = 1  # Lógica de evento provisória
        ingresso_id = None
        vip_id = None
        data = datetime.now()

        ingressos_validos = ["ING123", "ING456", "ING789"]
        lista_vip = ["Jair Messias Bolsonaro", "Luiz Inácio Lula Da Silva", "Lula", "Carlos Bolsonaro", "Emmanuel Macron", "Bolsonaro"]

        p = nome in lista_vip
        q = ingresso in ingressos_validos
        r = validar_cpf(cpf)

        if (p or q) and r:
            status = "Liberado"
            motivo = None
            acesso = True
        else:
            status = "Negado"
            motivo = "Regras de acesso não atendidas"
            acesso = False

        # Persiste o registro de acesso no banco de dados.
        try:
            col_map = get_acessos_column_map()
            insert_cols = []
            insert_vals = {}
            # Constrói a query de inserção dinamicamente com base nas colunas encontradas.
            if col_map.get('nome'):
                insert_cols.append(col_map['nome'])
                insert_vals[col_map['nome']] = nome
            if col_map.get('cpf'):
                insert_cols.append(col_map['cpf'])
                insert_vals[col_map['cpf']] = re.sub(r'\D','',cpf)
            if col_map.get('data'):
                insert_cols.append(col_map['data'])
                insert_vals[col_map['data']] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if col_map.get('status'):
                insert_cols.append(col_map['status'])
                insert_vals[col_map['status']] = status
            if col_map.get('motivo') and motivo:
                insert_cols.append(col_map['motivo'])
                insert_vals[col_map['motivo']] = motivo

            if insert_cols:
                cols_sql = ','.join(insert_cols)
                params_sql = ','.join([f":{c}" for c in insert_cols])
                sql_insert = text(f"INSERT INTO acessos ({cols_sql}) VALUES ({params_sql})")
                db.session.execute(sql_insert, insert_vals)
                db.session.commit()
            else:
                # Fallback: usa o modelo ORM se a detecção de colunas falhar.
                novo = Acesso(
                    nome=nome, ingresso=ingresso, cpf=cpf,
                    data=datetime.now().isoformat(), status=status
                )
                db.session.add(novo)
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao inserir acesso no banco de dados: {e}")

        resultado = f"Acesso {status}!"

    return render_template(
        'index.html', acesso=acesso,
        mensagem=resultado, logica=f"Lógica usada: (p: {p}, q: {q}, r: {r})"
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Página de login para administradores.

    Autentica o usuário contra a tabela 'users' e, em caso de sucesso,
    cria um token JWT e o armazena em um cookie HTTPOnly seguro.
    Suporta tanto requisições via formulário HTML quanto JSON.
    """
    if request.method == 'POST':
        # Permite receber credenciais via formulário ou JSON.
        if request.is_json:
            data = request.get_json()
            usuario = data.get('usuario')
            senha = data.get('senha')
        else:
            usuario = request.form.get('usuario')
            senha = request.form.get('senha')

        user = None
        try:
            user = User.query.filter_by(username=usuario).first()
        except Exception:
            user = None

        # Validação do usuário e da senha (hash).
        if not user or not check_password_hash(user.password_hash, senha):
            if request.is_json:
                return jsonify({"msg": "Credenciais inválidas."}), 401
            return render_template('login.html', erro="Credenciais inválidas.")

        # Verifica se o usuário tem permissão de administrador.
        if not user.is_admin or int(user.is_admin) != 1:
            if request.is_json:
                return jsonify({"msg": "Acesso permitido apenas para administradores."}), 403
            return render_template('login.html', erro="Acesso permitido apenas para administradores.")

        # Gera o token de acesso e o armazena no cookie.
        access_token = create_access_token(identity=usuario)
        if request.is_json:
            return jsonify(access_token=access_token)
        else:
            resp = make_response(redirect(url_for('relatorio')))
            set_access_cookies(resp, access_token)
            session['admin'] = True # Mantém sessão legada se necessário
            return resp

    return render_template('login.html')


@app.route('/logout')
def logout():
    """
    Realiza o logout do administrador.

    Limpa a sessão do Flask e remove o cookie JWT do navegador,
    invalidando a autenticação.
    """
    session.pop('admin', None)
    resp = make_response(redirect(url_for('login')))
    unset_jwt_cookies(resp) # Remove o cookie JWT.
    return resp


# --- Rotas Protegidas (Acesso de Administrador) ---

@app.route('/relatorio')
@jwt_required()
def relatorio():
    """
    Exibe o relatório de todos os acessos registrados.
    
    Esta rota é protegida e exige um JWT válido. A cada acesso,
    verifica novamente se o usuário no token ainda é um administrador.
    """
    # Verificação de identidade e permissão a cada requisição.
    usuario = get_jwt_identity()
    user = User.query.filter_by(username=usuario).first()
    if not user or int(user.is_admin) != 1:
        return redirect(url_for('login'))

    # Monta a query dinamicamente com base nas colunas da tabela 'acessos'.
    col_map = get_acessos_column_map()
    nome_col = col_map.get('nome') or 'nome'
    cpf_col = col_map.get('cpf') or 'cpf'
    data_col = col_map.get('data') or 'data'
    status_col = col_map.get('status') or 'status'
    motivo_col = col_map.get('motivo')

    filtro_status = request.args.get('status')

    campos = f"{nome_col} as nome, {cpf_col} as cpf, {data_col} as data, {status_col} as status"
    if motivo_col:
        campos += f", {motivo_col} as motivo"
    
    query = f"SELECT {campos} FROM acessos WHERE 1=1"
    params = {}
    if filtro_status:
        query += f" AND {status_col} = :status"
        params['status'] = filtro_status

    resultado = db.session.execute(text(query), params)
    dados = [dict(row._mapping) for row in resultado.fetchall()]

    # Calcula estatísticas para exibição no template
    total = len(dados)
    liberados = len([d for d in dados if d['status'] == 'Liberado'])
    negados = len([d for d in dados if d['status'] == 'Negado'])

    return render_template('relatorio.html', dados=dados, total=total, liberados=liberados, negados=negados)


@app.route('/exportar_csv')
@jwt_required()
def exportar_csv():
    """
    Gera e fornece o download de um arquivo CSV com todos os acessos.
    Rota protegida para administradores.
    """
    usuario = get_jwt_identity()
    user = User.query.filter_by(username=usuario).first()
    if not user or int(user.is_admin) != 1:
        return redirect(url_for('login'))

    col_map = get_acessos_column_map()
    nome_col = col_map.get('nome') or 'nome'
    cpf_col = col_map.get('cpf') or 'cpf'
    data_col = col_map.get('data') or 'data'
    status_col = col_map.get('status') or 'status'
    motivo_col = col_map.get('motivo')

    campos = f"{nome_col} as nome, {cpf_col} as cpf, {data_col} as data, {status_col} as status"
    if motivo_col:
        campos += f", {motivo_col} as motivo"

    resultado = db.session.execute(text(f"SELECT {campos} FROM acessos"))
    dados = resultado.fetchall()

    output = StringIO()
    writer = csv.writer(output)
    
    # Cabeçalhos do arquivo CSV
    headers = ['Nome', 'CPF', 'Data', 'Status']
    if motivo_col:
        headers.append('Motivo')
    writer.writerow(headers)

    for row in dados:
        # Normaliza a linha de dados, que pode ser um objeto RowMapping ou uma tupla.
        try:
            nome = row['nome']
            cpf = row['cpf']
            data = row['data']
            status = row['status']
            motivo = row.get('motivo') if motivo_col else ''
            writer.writerow([nome, cpf, data, status, motivo] if motivo_col else [nome, cpf, data, status])
        except (TypeError, KeyError):
            # Fallback para acesso por índice numérico
            writer.writerow(list(row))

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment; filename=relatorio_acessos.csv"}
    )


@app.route('/limpar_registros', methods=['POST'])
@jwt_required()
def limpar_registros():
    """
    Remove todos os registros da tabela 'acessos'.
    Rota protegida para administradores.
    """
    usuario = get_jwt_identity()
    user = User.query.filter_by(username=usuario).first()
    if not user or int(user.is_admin) != 1:
        return redirect(url_for('login'))

    db.session.execute(text("DELETE FROM acessos"))
    db.session.commit()
    return redirect(url_for('relatorio'))


@app.route('/controle')
@jwt_required()
def controle():
    """Página de controle para listar todos os eventos."""
    usuario = get_jwt_identity()
    user = User.query.filter_by(username=usuario).first()
    if not user or int(user.is_admin) != 1:
        return redirect(url_for('login'))

    eventos = Evento.query.order_by(Evento.data_inicio).all()
    return render_template('controle.html', eventos=eventos, agora=datetime.now())


@app.route('/evento/criar', methods=['GET', 'POST'])
@jwt_required()
def criar_evento():
    """Página com formulário para criar um novo evento."""
    usuario = get_jwt_identity()
    user = User.query.filter_by(username=usuario).first()
    if not user or int(user.is_admin) != 1:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nome = request.form['nome']
        data_inicio = datetime.strptime(request.form['data_inicio'], "%Y-%m-%dT%H:%M")
        data_fim = datetime.strptime(request.form['data_fim'], "%Y-%m-%dT%H:%M")
        local = request.form.get('local')
        descricao = request.form.get('descricao')

        novo_evento = Evento(nome=nome, data_inicio=data_inicio, data_fim=data_fim, local=local, descricao=descricao)
        db.session.add(novo_evento)
        db.session.commit()
        return redirect(url_for('controle'))

    return render_template('criar_evento.html')


@app.route('/evento/<int:evento_id>/apagar', methods=['POST'])
@jwt_required()
def apagar_evento(evento_id):
    """Rota para apagar um evento específico."""
    usuario = get_jwt_identity()
    user = User.query.filter_by(username=usuario).first()
    if not user or int(user.is_admin) != 1:
        return redirect(url_for('login'))

    evento = Evento.query.get_or_404(evento_id)
    db.session.delete(evento)
    db.session.commit()
    return redirect(url_for('controle'))


@app.route('/evento/<int:evento_id>')
@jwt_required()
def relatorio_evento(evento_id):
    """Exibe o relatório de acessos para um evento específico."""
    usuario = get_jwt_identity()
    user = User.query.filter_by(username=usuario).first()
    if not user or int(user.is_admin) != 1:
        return redirect(url_for('login'))

    evento = Evento.query.get_or_404(evento_id)
    query = text("SELECT nome, cpf, data, status FROM acessos WHERE evento_id = :evento_id")
    resultado = db.session.execute(query, {"evento_id": evento_id})
    dados = resultado.fetchall()

    total = len(dados)
    liberados = len([d for d in dados if d[3] == 'Liberado'])
    negados = len([d for d in dados if d[3] == 'Negado'])

    return render_template('relatorio.html', dados=dados, total=total, liberados=liberados, negados=negados, evento=evento)


# --- Ponto de Entrada da Aplicação ---

if __name__ == '__main__':
    app.run(debug=True)