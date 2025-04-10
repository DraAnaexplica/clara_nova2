import os
import requests
import logging
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from dotenv import load_dotenv

# Configuração de Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carrega variáveis de ambiente
load_dotenv()
logging.info("Variáveis .env carregadas.")

# Importações painel (tentativa)
try:
    from painel import (
        criar_tabela_tokens, inserir_token, listar_tokens,
        excluir_token, criar_tabela_chat_history,
        add_chat_message, get_chat_history
    )
    PAINEL_IMPORTADO = True
    logging.info("Painel importado com sucesso.")
except ImportError as e:
    logging.warning(f"Falha ao importar painel: {e}")
    PAINEL_IMPORTADO = False
    def criar_tabela_tokens(): pass
    def inserir_token(uid, dias): return f"fake_token_{uid}"
    def listar_tokens(): return []
    def excluir_token(tok): pass
    def criar_tabela_chat_history(): pass
    def add_chat_message(ut, r, c): return True
    def get_chat_history(ut, lim): return []

# Fallback pytz
try:
    from pytz import timezone
    PYTZ_IMPORTADO = True
except ImportError:
    PYTZ_IMPORTADO = False
    class timezone:
        def __init__(self, tz_name): pass

# Flask App
app = Flask(__name__)
app.secret_key = os.getenv("PAINEL_SENHA", "chave-secreta-padrao")

# Configuração da IA
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
AI_MODEL = "deepseek/deepseek-chat-v3-0324"

# Prompt do sistema
SYSTEM_PROMPT = "Assistente."
try:
    with open("system_prompt.txt", 'r', encoding='utf-8') as f:
        SYSTEM_PROMPT = f.read().strip()
except Exception as e:
    logging.warning(f"Prompt padrão usado: {e}")

# Criação das tabelas
try:
    criar_tabela_tokens()
    criar_tabela_chat_history()
except Exception as e:
    logging.warning(f"Erro criando tabelas: {e}")

# Função OpenRouter
def get_ai_response(messages_to_send: list) -> str:
    if not OPENROUTER_API_KEY:
        raise ValueError("Chave API ausente.")
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": request.url_root,
        "X-Title": "Dra Ana App"
    }
    payload = {
        "model": AI_MODEL,
        "messages": messages_to_send,
        "temperature": 0.9
    }
    response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=45)
    response.raise_for_status()
    data = response.json()
    return data['choices'][0]['message']['content'].strip()

# Rotas principais
@app.route("/")
def index():
    return redirect(url_for("instalar"))

@app.route("/instalar")
def instalar():
    if session.get('acesso_concluido') and session.get('user_token'):
        return redirect(url_for('dra_ana_route'))
    return render_template("formulario_acesso.html", exibir_instalador=True)

@app.route("/acesso", methods=["GET", "POST"])
def acesso_usuario():
    if request.method == "POST":
        nome = request.form.get("nome")
        telefone = request.form.get("telefone")
        if not nome or not telefone:
            return render_template("formulario_acesso.html", sucesso=False, erro="Nome e telefone são obrigatórios."), 400
        user_id = f"{nome} ({telefone})"
        try:
            token = inserir_token(user_id, 7)
            session['acesso_concluido'] = True
            session['user_token'] = token
            return redirect(url_for("dra_ana_route"))
        except Exception as e:
            logging.exception("Erro ao gerar token")
            return render_template("formulario_acesso.html", sucesso=False, erro="Erro ao gerar acesso."), 500
    return render_template("formulario_acesso.html")

@app.route("/dra-ana")
def dra_ana_route():
    if not session.get('acesso_concluido') or not session.get('user_token'):
        return redirect(url_for('instalar'))

    try:
        import psycopg2
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        with conn.cursor() as cur:
            cur.execute("SELECT validade_em FROM tokens WHERE token = %s", (session['user_token'],))
            resultado = cur.fetchone()
        if not resultado:
            return redirect(url_for("resetar_acesso"))
        validade = resultado[0]
        agora = datetime.utcnow().replace(tzinfo=validade.tzinfo)
        if validade < agora:
            return redirect(url_for("resetar_acesso"))
    except Exception as e:
        logging.exception("Erro ao validar token no dra-ana")
        return redirect(url_for("resetar_acesso"))

    return render_template("chat.html")

@app.route("/chat", methods=["POST"])
def chat_endpoint():
    user_token = session.get('user_token')
    if not user_token:
        return jsonify({"error": "Não autorizado"}), 403

    try:
        data = request.get_json()
        user_message = data.get("mensagem")
        if not user_message:
            raise ValueError("Mensagem inválida")

        add_chat_message(user_token, 'user', user_message)
        historico = get_chat_history(user_token, 20)
        mensagens = [{"role": "system", "content": SYSTEM_PROMPT}] + historico
        resposta = get_ai_response(mensagens)
        add_chat_message(user_token, 'assistant', resposta)
        return jsonify({"response": resposta})
    except Exception as e:
        logging.exception("Erro no endpoint /chat")
        return jsonify({"error": "Erro interno"}), 500

@app.route("/validar-token", methods=["POST"])
def validar_token():
    if not session.get('user_token'):
        return jsonify({"valido": False, "motivo": "Sessão inválida."}), 401

    token = session['user_token']
    try:
        import psycopg2
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        with conn.cursor() as cur:
            cur.execute("SELECT validade_em FROM tokens WHERE token = %s", (token,))
            resultado = cur.fetchone()
        if not resultado:
            return jsonify({"valido": False, "motivo": "Token não encontrado"}), 403
        validade = resultado[0]
        agora = datetime.utcnow().replace(tzinfo=validade.tzinfo)
        if validade < agora:
            return jsonify({"valido": False, "motivo": "Token expirado"}), 403
        return jsonify({"valido": True})
    except Exception as e:
        logging.exception("Erro ao validar token")
        return jsonify({"valido": False, "motivo": "Erro interno"}), 500

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        senha = request.form.get("senha")
        if senha == os.getenv("PAINEL_SENHA"):
            session["autenticado"] = True
            return redirect(url_for("painel"))
        return "❌ Senha incorreta", 401
    return '''<form method="POST"><label>Senha Painel: <input type="password" name="senha" required></label><button type="submit">Entrar</button></form>'''

@app.route("/logout")
def logout():
    session.pop("autenticado", None)
    return redirect(url_for("login"))

@app.route("/painel", methods=["GET", "POST"])
def painel():
    if not session.get("autenticado"):
        return redirect(url_for("login"))
    token_gerado = None
    erro = ""
    if request.method == "POST":
        user_id = request.form.get("user_id")
        dias = int(request.form.get("dias_validade", 7))
        try:
            token_gerado = inserir_token(user_id, dias)
        except Exception as e:
            erro = "Erro ao gerar token"
            logging.exception("Erro gerar token no painel")
    tokens = listar_tokens()
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    return render_template("painel.html", token_gerado=token_gerado, tokens=tokens, now=now, erro=erro)

@app.route("/excluir_token", methods=["POST"])
def excluir_token_route():
    if not session.get("autenticado"):
        return redirect(url_for("login"))
    token = request.form.get("token")
    try:
        excluir_token(token)
    except Exception as e:
        logging.exception("Erro ao excluir token")
    return redirect(url_for("painel"))

@app.route("/resetar_acesso")
def resetar_acesso():
    session.pop("acesso_concluido", None)
    session.pop("user_token", None)
    return "Acesso resetado. <a href='/'>Clique aqui para voltar</a>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() in ["true", "1", "t"]
    app.run(debug=debug, host="0.0.0.0", port=port)
