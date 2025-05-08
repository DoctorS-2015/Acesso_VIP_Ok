from flask import Flask, render_template, request, redirect, url_for, session, Response
import sqlite3
import re
from datetime import datetime
from io import StringIO
import csv

app = Flask(__name__)
app.secret_key = 'chave_secreta_segura'

def validar_cpf(cpf):
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    soma1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    dig1 = (soma1 * 10 % 11) % 10
    soma2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    dig2 = (soma2 * 10 % 11) % 10
    return cpf[-2:] == f"{dig1}{dig2}"

def criar_banco():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS acessos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            ingresso TEXT,
            cpf TEXT,
            data TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    criar_banco()
    resultado = None
    acesso = None
    p = q = r = False

    if request.method == 'POST':
        nome = request.form['nome']
        ingresso = request.form['ingresso']
        cpf = request.form['cpf']
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        ingressos_validos = ["ING123", "ING456", "ING789"]
        lista_vip = ["Jair Messias Bolsonaro", "Luiz Inácio Lula Da Silva", "Lula", "Carlos Bolsonaro", "Emmanuel Macron", "Bolsonaro"]
       # cpfs_validos = ["12345678909", "98765432100", "11122233344"]

        p = nome in lista_vip
        q = ingresso in ingressos_validos
        r = validar_cpf(cpf) # and cpf in cpfs_validos

        acesso = (p or q) and r
        status = "Liberado" if acesso else "Negado"

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO acessos (nome, ingresso, cpf, data, status) VALUES (?, ?, ?, ?, ?)',
                       (nome, ingresso, cpf, data, status))
        conn.commit()
        conn.close()

        resultado = f"Acesso {status}!"

    return render_template('index.html', acesso=acesso, mensagem=resultado, logica=f"Lógica usada: (p: {p}, q: {q}, r: {r})")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        if usuario == 'admin' and senha == '123':
            session['admin'] = True
            return redirect(url_for('relatorio'))
        else:
            return render_template('login.html', erro="Credenciais inválidas.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

@app.route('/relatorio')
def relatorio():
    if not session.get('admin'):
        return redirect(url_for('login'))

    filtro_ingresso = request.args.get('ingresso')
    filtro_status = request.args.get('status')
    filtro_data_inicio = request.args.get('data_inicio')
    filtro_data_fim = request.args.get('data_fim')

    query = 'SELECT nome, ingresso, cpf, data, status FROM acessos WHERE 1=1'
    params = []

    if filtro_ingresso:
        query += ' AND ingresso = ?'
        params.append(filtro_ingresso)
    if filtro_status:
        query += ' AND status = ?'
        params.append(filtro_status)
    if filtro_data_inicio:
        query += ' AND date(data) >= date(?)'
        params.append(filtro_data_inicio)
    if filtro_data_fim:
        query += ' AND date(data) <= date(?)'
        params.append(filtro_data_fim)

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    dados = cursor.fetchall()

    total = len(dados)
    liberados = len([d for d in dados if d[4] == 'Liberado'])
    negados = len([d for d in dados if d[4] == 'Negado'])

    conn.close()
    return render_template('relatorio.html', dados=dados, total=total, liberados=liberados, negados=negados)

@app.route('/exportar_csv')
def exportar_csv():
    filtro_ingresso = request.args.get('ingresso')
    filtro_status = request.args.get('status')
    filtro_data_inicio = request.args.get('data_inicio')
    filtro_data_fim = request.args.get('data_fim')

    query = 'SELECT nome, ingresso, cpf, data, status FROM acessos WHERE 1=1'
    params = []

    if filtro_ingresso:
        query += ' AND ingresso = ?'
        params.append(filtro_ingresso)
    if filtro_status:
        query += ' AND status = ?'
        params.append(filtro_status)
    if filtro_data_inicio:
        query += ' AND date(data) >= date(?)'
        params.append(filtro_data_inicio)
    if filtro_data_fim:
        query += ' AND date(data) <= date(?)'
        params.append(filtro_data_fim)

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    dados = cursor.fetchall()
    conn.close()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Nome', 'Ingresso', 'CPF', 'Data', 'Status'])
    writer.writerows(dados)
    output.seek(0)

    return Response(output.getvalue(), mimetype='text/csv',
                    headers={"Content-Disposition": "attachment; filename=relatorio_acessos.csv"})

@app.route('/limpar_registros', methods=['POST'])
def limpar_registros():
    if not session.get('admin'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM acessos")
    conn.commit()
    conn.close()
    return redirect(url_for('relatorio'))
    
if __name__ == '__main__':
    app.run(debug=True)
