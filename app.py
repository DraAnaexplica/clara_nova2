# app.py (FINALMENTE CORRIGIDO - SEM ERROS DE SINTAXE)

import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from dotenv import load_dotenv
import logging
from datetime import datetime
import json

# Configuração de Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carrega variáveis de ambiente do .env
load_dotenv_success = load_dotenv(override=True, verbose=True)
logging.info(f"Arquivo .env carregado com sucesso? {load_dotenv_success}")

# Importação Segura do Módulo 'painel'
try:
    from painel import ( criar_tabela_tokens, inserir_token, listar_tokens, excluir_token, criar_tabela_chat_history, add_chat_message, get_chat_history )
    PAINEL_IMPORTADO = True
    logging.info("Módulo 'painel' e funções de chat importados com sucesso.")
except ImportError as e:
    logging.warning(f"Módulo 'painel' não encontrado ou com erro: {e}. Usando placeholders.")
    PAINEL_IMPORTADO = False
    # Placeholders Corrigidos (um def por linha)
    def criar_tabela_tokens(): logging.info("Placeholder: Criar tabela tokens")
    def inserir_token(uid, dias): logging.info(f"Placeholder: Inserir token {uid}"); return {"token": f"fake_token_{uid}"}
    def listar_tokens(): logging.info("Placeholder: Listar tokens"); return []
    def excluir_token(tok): logging.info(f"Placeholder: Excluir token {tok}")
    def criar_tabela_chat_history(): logging.info("Placeholder: Criar tabela chat")
    def add_chat_message(ut, r, c): logging.info(f"Placeholder: Add chat msg {ut[:8]} R:{r}"); return True
    def get_chat_history(ut, lim): logging.info(f"Placeholder: Get chat hist {ut[:8]}"); return []

# Importa pytz (com fallback corrigido)
try:
    from pytz import timezone
    PYTZ_IMPORTADO = True
except ImportError:
    logging.warning("Biblioteca 'pytz' não encontrada. Usando UTC.")
    PYTZ_IMPORTADO = False
    class timezone: # Placeholder com indentação correta
        def __init__(self, tz_name):
            pass # << CORREÇÃO AQUI

# Configuração do App Flask
app = Flask(__name__)
app.secret_key = os.getenv("PAINEL_SENHA", "configure-uma-chave-secreta-forte-no-env")
if app.secret_key == "configure-uma-chave-secreta-forte-no-env": logging.warning("PAINEL_SENHA não definida!")

# Configurações da IA
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
AI_MODEL = "deepseek/deepseek-chat" # Mantendo DeepSeek
logging.info(f"Usando modelo de IA: {AI_MODEL}")

# Ler SYSTEM_PROMPT do arquivo
SYSTEM_PROMPT_FILE = "system_prompt.txt"; SYSTEM_PROMPT = "Assistente."
try:
    with open(SYSTEM_PROMPT_FILE, 'r', encoding='utf-8') as f: SYSTEM_PROMPT = f.read().strip()
    if SYSTEM_PROMPT and SYSTEM_PROMPT != "Assistente.": logging.info(f"Prompt OK de '{SYSTEM_PROMPT_FILE}'.")
    else: logging.warning(f"Usando prompt padrão. '{SYSTEM_PROMPT_FILE}' vazio/não encontrado?")
except Exception as e: logging.error(f"Erro lendo '{SYSTEM_PROMPT_FILE}': {e}", exc_info=True)
if not OPENROUTER_API_KEY: logging.error("FATAL: OPENROUTER_API_KEY não carregada!")

# Criação das Tabelas na Inicialização
try:
    if PAINEL_IMPORTADO: criar_tabela_tokens(); criar_tabela_chat_history()
except Exception as e: logging.error(f"Erro ao criar tabelas: {e}", exc_info=True)

# --- Função Auxiliar API OpenRouter (Corrigida e Revisada) ---
def get_ai_response(messages_to_send: list) -> str:
    if not OPENROUTER_API_KEY: raise ValueError("Chave API não configurada.")
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json", "HTTP-Referer": request.url_root if request else "http://localhost:5000", "X-Title": "Dra Ana App"}
    payload = {"model": AI_MODEL, "messages": messages_to_send}
    logging.info(f"Enviando {len(messages_to_send)} msgs para {AI_MODEL}")
    try: logging.debug(f"Payload (parcial): {json.dumps(payload, ensure_ascii=False)[:500]}...")
    except Exception: logging.debug("Nao foi possivel logar payload json.")
    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=45); response.raise_for_status()
        api_result=response.json();
        if isinstance(api_result, dict) and 'choices' in api_result and api_result['choices'] and isinstance(api_result['choices'][0], dict) and 'message' in api_result['choices'][0] and isinstance(api_result['choices'][0]['message'], dict) and 'content' in api_result['choices'][0]['message']:
            ai_content = api_result['choices'][0]['message']['content']; logging.info(f"Resposta OK: {ai_content[:100]}..."); return ai_content.strip() if isinstance(ai_content, str) else str(ai_content)
        else: logging.error(f"Resposta API inesperada: {api_result}"); raise ValueError("Resposta API inesperada.")
    except requests.exceptions.Timeout: logging.error("Timeout API."); raise TimeoutError("IA demorou.")
    # Bloco except HTTPError com formatação CORRETA
    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code
        logging.error(f"Erro HTTP API: {status_code} - {http_err.response.text}")
        if status_code == 401: raise PermissionError("Erro auth API.")
        elif status_code == 402: raise ConnectionRefusedError("Créditos/Limite API.")
        elif status_code == 429: raise ConnectionRefusedError("Limite taxa API.")
        else: raise ConnectionError(f"Erro API ({status_code}).")
    except requests.exceptions.RequestException as e: logging.error(f"Erro rede API: {e}"); raise ConnectionError("Erro rede IA.")
    except Exception as e: logging.exception("Erro inesperado resposta IA."); raise ValueError("Erro processar resposta IA.")

# --- Rotas ---
@app.route("/")
def index(): return redirect(url_for("instalar"))
@app.route("/instalar")
def instalar():
    if session.get('acesso_concluido') and session.get('user_token'): return redirect(url_for('dra_ana_route'))
    return render_template("formulario_acesso.html", exibir_instalador=True)
@app.route("/acesso", methods=["GET", "POST"])
def acesso_usuario():
    if request.method == "POST":
        nome=request.form.get("nome"); telefone=request.form.get("telefone")
        if not nome or not telefone: return render_template("formulario_acesso.html", sucesso=False, erro="Nome/telefone obrigatórios."), 400
        user_id=f"{nome} ({telefone})"; dias=7
        try:
            if PAINEL_IMPORTADO: token=inserir_token(user_id,dias); assert token
            else: logging.warning("Simulando token."); token=f"fake_{user_id}"
            session['acesso_concluido']=True; session['user_token']=token
            logging.info(f"Acesso OK: {user_id}, Token:{token[:8]}...")
            return redirect(url_for('dra_ana_route'))
        except Exception as e: logging.error(f"Erro inserir token {user_id}: {e}",exc_info=True); return render_template("formulario_acesso.html",sucesso=False,erro="Erro processar acesso."),500
    if session.get('acesso_concluido') and session.get('user_token'): return redirect(url_for('dra_ana_route'))
    else: session.pop('acesso_concluido',None); session.pop('user_token',None); session.modified=True; return render_template("formulario_acesso.html",sucesso=False)
@app.route("/dra-ana")
def dra_ana_route():
    if not session.get('acesso_concluido') or not session.get('user_token'): return redirect(url_for('instalar'))
    return render_template("chat.html")
@app.route("/chat", methods=["POST"])
def chat_endpoint():
    user_token = session.get('user_token')
    if not user_token or not session.get('acesso_concluido'): return jsonify({"error": "Não autorizado"}), 403
    try:
        data=request.get_json(); assert data
        user_message=data.get("mensagem"); assert user_message and isinstance(user_message,str) and user_message.strip()
        logging.info(f"Msg (T:{user_token[:8]}): {user_message[:100]}...")
        if PAINEL_IMPORTADO: add_chat_message(user_token, 'user', user_message)
        else: logging.warning("Placeholder: Não salvando msg user.")
        chat_history=[]
        if PAINEL_IMPORTADO: chat_history=get_chat_history(user_token,limit=20)
        else: logging.warning("Placeholder: Não buscando histórico.")
        messages_to_send=[{"role":"system","content":SYSTEM_PROMPT}] + chat_history
        try:
            ai_response=get_ai_response(messages_to_send)
            if PAINEL_IMPORTADO: add_chat_message(user_token,'assistant',ai_response)
            else: logging.warning("Placeholder: Não salvando msg assistant.")
            return jsonify({"response": ai_response})
        except(ValueError,ConnectionError,PermissionError,TimeoutError,ConnectionRefusedError) as e: error_message=str(e); sc=503 if isinstance(e,(TimeoutError,ConnectionError,ConnectionRefusedError)) else 401 if isinstance(e,PermissionError) else 500; return jsonify({"error":f"Erro IA: {error_message}"}), sc
        except Exception as e: logging.exception("Erro call get_ai_response."); return jsonify({"error": "Erro interno IA."}), 500
    except Exception as e: logging.exception("Erro geral /chat."); return jsonify({"error": "Erro interno servidor."}), 500
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        senha = request.form.get("senha"); sp = os.getenv("PAINEL_SENHA")
        if not sp: logging.error("PAINEL_SENHA não config!"); return "Erro config.", 500
        if senha == sp: session["autenticado"] = True; logging.info("Admin auth OK."); return redirect(url_for("painel"))
        else: logging.warning("Login painel falhou."); return "❌ Senha incorreta", 401
    return'''<form method="POST"><label>Senha Painel: <input type="password" name="senha" required></label><button type="submit">Entrar</button></form>'''
@app.route("/logout")
def logout():
    admin_antes=session.pop("autenticado",None);session.modified=True
    if admin_antes: logging.info("Admin deslogado.")
    return redirect(url_for("login"))
@app.route("/painel", methods=["GET", "POST"])
def painel():
    if not session.get("autenticado"): return redirect(url_for("login"))
    token_gerado_info=None; erro_painel="" # <<< Correção aqui
    if request.method == "POST" and "user_id" in request.form:
        user_id=request.form.get("user_id")
        try:
            dias_str=request.form.get("dias_validade",'7'); assert dias_str.isdigit() and int(dias_str)>0
            dias=int(dias_str)
            if PAINEL_IMPORTADO: token_gerado_info=inserir_token(user_id,dias); logging.info(f"Admin gerou token {user_id}/{dias}d.")
            else: erro_painel="Painel não importado."
        except(ValueError,AssertionError): erro_painel="Dias inválido."; logging.warning(erro_painel)
        except Exception as e: logging.exception("Erro gerar token painel."); erro_painel="Erro inesperado."
    tokens=[];
    try:
        if PAINEL_IMPORTADO: tokens=listar_tokens()
        else: msg_e="Painel não importado."; erro_painel+=(" "+msg_e if erro_painel else msg_e)
    except Exception as e: logging.exception("Erro listar tokens."); msg_e="Erro listar tokens."; erro_painel+=(" "+msg_e if erro_painel else msg_e)
    now_tz=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC');
    if PYTZ_IMPORTADO:
        try: now_tz=datetime.now(timezone("America/Sao_Paulo")).strftime('%Y-%m-%d %H:%M:%S %Z%z')
        except Exception as e: logging.warning(f"Erro timezone: {e}. Usando UTC.")
    return render_template("painel.html",token_gerado=token_gerado_info,tokens=tokens,now=now_tz,erro=erro_painel)
@app.route("/excluir_token", methods=["POST"])
def excluir_token_route():
    if not session.get("autenticado"): return redirect(url_for("login"))
    token=request.form.get("token")
    if token:
        try:
            if PAINEL_IMPORTADO: excluir_token(token); logging.info(f"Admin excluiu token: {token[:8]}...")
            else: logging.error("Painel não importado.")
        except Exception as e: logging.exception(f"Erro excluir token {token[:8]}...")
    else: logging.warning("Exclusão sem token.")
    return redirect(url_for("painel"))
@app.route("/resetar_acesso")
def resetar_acesso():
    session.pop('acesso_concluido',None); session.pop('user_token',None); session.modified=True
    logging.info("Sessão de acesso resetada.")
    return"Sessão de acesso e histórico de chat resetados. <a href='/'>Voltar ao início</a>"
if __name__ == "__main__":
    port=int(os.environ.get('PORT',5000)); debug_mode=os.environ.get('FLASK_DEBUG','False').lower() in ['true','1','t']
    logging.info(f"Iniciando app em host=0.0.0.0, port={port}, debug={debug_mode}")
    app.run(debug=debug_mode,host='0.0.0.0',port=port)
