# app.py - versão atualizada com JWT e integração com tabela users (MySQL/MariaDB)
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

# ALTERAÇÃO: import de Flask-JWT-Extended para criar e validar tokens JWT
# Adicionei verify_jwt_in_request e NoAuthorizationError para eventuais validações/handling.
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required,
    get_jwt_identity, set_access_cookies, unset_jwt_cookies,
    verify_jwt_in_request
)
from flask_jwt_extended.exceptions import NoAuthorizationError

# carregar .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'chave_fallback')

# Config DB (usa DATABASE_URL do .env; se não definido, cai no fallback sqlite)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 'sqlite:///fallback.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ALTERAÇÃO: configurações básicas do JWT (cookies HTTPOnly)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', os.getenv('SECRET_KEY', 'jwt_fallback'))
app.config['JWT_TOKEN_LOCATION'] = ['cookies']            # usamos cookie HTTPOnly por padrão
app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
app.config['JWT_COOKIE_CSRF_PROTECT'] = False            # DESLIGADO EM DEV; em produção ligue e implemente CSRF
app.config['JWT_COOKIE_SECURE'] = False                  # False em HTTP local; coloque True em produção (HTTPS)
app.config['JWT_COOKIE_SAMESITE'] = 'Lax'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

db = SQLAlchemy(app)
jwt = JWTManager(app)

# --- ALTERAÇÃO: handler global para casos não autorizados ---
@jwt.unauthorized_loader
def unauthorized_callback(callback):
    """
    ALTERAÇÃO:
    Em vez de a biblioteca devolver uma mensagem 'Missing cookie "access_token_cookie"',
    redirecionamos para a página de login. Mantemos o decorador @jwt_required()
    nas rotas; quando não houver token válido, o usuário será redirecionado.
    """
    return redirect(url_for('login'))


# Modelo mapeando tabela existente 'acessos'
class Acesso(db.Model):
    __tablename__ = 'acessos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255))
    ingresso = db.Column(db.String(100))
    cpf = db.Column(db.String(20))
    data = db.Column(db.String(50))
    status = db.Column(db.String(50))

# Modelo User mapeando a tabela real 'users' no seu banco
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Integer, nullable=True)

# ALTERAÇÃO: Modelo Evento com base no DESCRIBE eventos
class Evento(db.Model):
    __tablename__ = 'eventos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    data_inicio = db.Column(db.DateTime, nullable=False)
    data_fim = db.Column(db.DateTime, nullable=False)
    local = db.Column(db.String(255))
    descricao = db.Column(db.Text)

# Função validar CPF
def validar_cpf(cpf):
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    soma1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    dig1 = (soma1 * 10 % 11) % 10
    soma2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    dig2 = (soma2 * 10 % 11) % 10
    return cpf[-2:] == f"{dig1}{dig2}"

# Função utilitária para mapear colunas em acessos
def get_acessos_column_map():
    col_map = {
        'nome': None,
        'cpf': None,
        'data': None,
        'status': None,
        'motivo': None
    }
    try:
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
        try:
            insp = db.engine.execute(text("SELECT * FROM acessos LIMIT 1"))
            cols = [c for c in insp.keys()]
        except Exception:
            cols = []

    normalized = [c.lower() for c in cols]
    for c in normalized:
        if c in ('nome', 'nome_acesso', 'name'):
            if not col_map['nome']:
                col_map['nome'] = c
        if c in ('cpf', 'cpf_acesso'):
            if not col_map['cpf']:
                col_map['cpf'] = c
        if c in ('data', 'data_hora', 'datahora', 'created_at'):
            if not col_map['data']:
                col_map['data'] = c
        if c in ('status', 'status_acesso'):
            if not col_map['status']:
                col_map['status'] = c
        if c in ('motivo', 'motivo_negado', 'reason'):
            if not col_map['motivo']:
                col_map['motivo'] = c

    for key in col_map:
        if col_map[key] is None and len(normalized) > 0:
            for cand in normalized:
                if key in cand:
                    col_map[key] = cand
                    break
    return col_map

@app.route('/', methods=['GET', 'POST'])
def index():
    resultado = None
    acesso = None
    p = q = r = False

    if request.method == 'POST':
        nome = request.form['nome']
        ingresso = request.form['ingresso']
        cpf = request.form['cpf']
        evento_id = 1   # provisório
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

        # Inserção adaptada: tentamos inserir nas colunas mais prováveis para compatibilidade
        try:
            col_map = get_acessos_column_map()
            # Construir insert dinâmico de acordo com colunas existentes
            insert_cols = []
            insert_vals = {}
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
                # fallback: usar ORM se nada detectado (pode falhar se modelo não bater)
                novo = Acesso(
                    nome=nome,
                    ingresso=ingresso,
                    cpf=cpf,
                    data=datetime.now().isoformat(),
                    status=status
                )
                db.session.add(novo)
                db.session.commit()
        except Exception as e:
            # em caso de erro, log e rollback mínimo
            db.session.rollback()
            print("Erro ao inserir acesso:", e)

        resultado = f"Acesso {status}!"

    return render_template(
        'index.html',
        acesso=acesso,
        mensagem=resultado,
        logica=f"Lógica usada: (p: {p}, q: {q}, r: {r})"
    )

# ALTERAÇÃO: rota /login atualizada para usar tabela users e criar JWT
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Suporta form ou JSON
        if request.is_json:
            data = request.get_json()
            usuario = data.get('usuario')
            senha = data.get('senha')
        else:
            usuario = request.form.get('usuario')
            senha = request.form.get('senha')

        # Buscar usuário na tabela users (modelo User mapeia essa tabela)
        user = None
        try:
            user = User.query.filter_by(username=usuario).first()
        except Exception:
            user = None

        if not user:
            # usuário não encontrado
            if request.is_json:
                return jsonify({"msg": "Credenciais inválidas."}), 401
            return render_template('login.html', erro="Credenciais inválidas.")

        # Verificar hash da senha
        if not check_password_hash(user.password_hash, senha):
            if request.is_json:
                return jsonify({"msg": "Credenciais inválidas."}), 401
            return render_template('login.html', erro="Credenciais inválidas.")

        # Verificar se é admin (somente admins podem acessar o painel)
        if not user.is_admin or int(user.is_admin) != 1:
            if request.is_json:
                return jsonify({"msg": "Acesso permitido apenas para administradores."}), 403
            return render_template('login.html', erro="Acesso permitido apenas para administradores.")

        # Criar token e setar cookie seguro
        access_token = create_access_token(identity=usuario)
        if request.is_json:
            return jsonify(access_token=access_token)
        else:
            resp = make_response(redirect(url_for('relatorio')))
            set_access_cookies(resp, access_token)  # ALTERAÇÃO: salva token em cookie HTTPOnly
            session['admin'] = True
            return resp

    return render_template('login.html')

# ALTERAÇÃO: logout remove cookie JWT e limpa session
@app.route('/logout')
def logout():
    session.pop('admin', None)
    resp = make_response(redirect(url_for('login')))
    unset_jwt_cookies(resp)  # remove cookie JWT
    return resp

# ALTERAÇÃO: rotas protegidas com @jwt_required() e validação de is_admin a cada request
@app.route('/relatorio')
@jwt_required()  # força que a rota só seja acessada com JWT válido
def relatorio():
    try:
        # garante que o token é válido (jwt_required já faz isso,
        # mas deixamos o try/except para redirecionar em caso de erro)
        verify_jwt_in_request()
    except exceptions.NoAuthorizationError:
        return redirect(url_for('login'))  # em vez de erro JSON, vai para login

    # pega o usuário logado a partir do token
    usuario = get_jwt_identity()

    # confirmar usuário e permissão no banco
    user = User.query.filter_by(username=usuario).first()
    if not user or int(user.is_admin) != 1:
        return redirect(url_for('login'))

    # montar SELECT adaptado às colunas reais
    col_map = get_acessos_column_map()
    # colunas padronizadas para exibição
    nome_col = col_map.get('nome') or 'nome'
    cpf_col = col_map.get('cpf') or 'cpf'
    data_col = col_map.get('data') or 'data'
    status_col = col_map.get('status') or 'status'
    motivo_col = col_map.get('motivo')  # pode ser None

    filtro_status = request.args.get('status')

    # montar query
    campos = f"{nome_col} as nome, {cpf_col} as cpf, {data_col} as data, {status_col} as status"
    if motivo_col:
        campos += f", {motivo_col} as motivo"
    query = f"SELECT {campos} FROM acessos WHERE 1=1"
    params = {}
    if filtro_status:
        query += " AND " + status_col + " = :status"
        params['status'] = filtro_status

    resultado = db.session.execute(text(query), params)
    dados = resultado.fetchall()

    total = len(dados)
    liberados = len([d for d in dados if d['status'] == 'Liberado' or d[3] == 'Liberado'])
    negados = len([d for d in dados if d['status'] == 'Negado' or d[3] == 'Negado'])

    return render_template('relatorio.html', dados=dados, total=total, liberados=liberados, negados=negados)

# ALTERAÇÃO: exportar_csv protegido com @jwt_required()
@app.route('/exportar_csv')
@jwt_required()
def exportar_csv():
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
    # headers
    headers = ['Nome', 'CPF', 'Data', 'Status']
    if motivo_col:
        headers.append('Motivo')
    writer.writerow(headers)

    for row in dados:
        # row pode ser RowMapping (acessível por nome) ou tupla; normalizamos
        try:
            nome = row['nome']
            cpf = row['cpf']
            data = row['data']
            status = row['status']
            motivo = row.get('motivo') if motivo_col else ''
            writer.writerow([nome, cpf, data, status, motivo] if motivo_col else [nome, cpf, data, status])
        except Exception:
            # fallback por índice
            writer.writerow(list(row))

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment; filename=relatorio_acessos.csv"}
    )

# ALTERAÇÃO: limpar_registros protegido e validando admin
@app.route('/limpar_registros', methods=['POST'])
@jwt_required()
def limpar_registros():
    usuario = get_jwt_identity()
    user = User.query.filter_by(username=usuario).first()
    if not user or int(user.is_admin) != 1:
        return redirect(url_for('login'))

    db.session.execute(text("DELETE FROM acessos"))
    db.session.commit()
    return redirect(url_for('relatorio'))
# --- Rota de controle dos eventos ---
@app.route('/controle')
@jwt_required()
def controle():
    usuario = get_jwt_identity()
    user = User.query.filter_by(username=usuario).first()
    if not user or int(user.is_admin) != 1:
        return redirect(url_for('login'))

    # ALTERAÇÃO: ordenação agora por data_inicio (existe no banco)
    eventos = Evento.query.order_by(Evento.data_inicio).all()
    return render_template('controle.html', eventos=eventos)

# --- Criar evento ---
@app.route('/evento/criar', methods=['GET', 'POST'])
@jwt_required()
def criar_evento():
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

# --- Apagar evento ---
@app.route('/evento/<int:evento_id>/apagar', methods=['POST'])
@jwt_required()
def apagar_evento(evento_id):
    usuario = get_jwt_identity()
    user = User.query.filter_by(username=usuario).first()
    if not user or int(user.is_admin) != 1:
        return redirect(url_for('login'))

    evento = Evento.query.get_or_404(evento_id)
    db.session.delete(evento)
    db.session.commit()
    return redirect(url_for('controle'))

# --- Relatório por evento ---
@app.route('/evento/<int:evento_id>')
@jwt_required()
def relatorio_evento(evento_id):
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

if __name__ == '__main__':
    app.run(debug=True)
