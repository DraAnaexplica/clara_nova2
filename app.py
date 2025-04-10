# app.py (Versão Final - Modelo DeepSeek e Erros Corrigidos)

import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from dotenv import load_dotenv
import logging
from datetime import datetime, timezone # Importa timezone de datetime
import json

# Configuração de Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carrega variáveis de ambiente do .env
load_dotenv_success = load_dotenv(override=True, verbose=True)
logging.info(f"Arquivo .env carregado com sucesso? {load_dotenv_success}")

# Importação Segura do Módulo 'painel'
try:
    from painel import ( criar_tabela_tokens, inserir_token, listar_tokens, excluir_token, criar_tabela_chat_history, add_chat_message, get_chat_history )
    PAINEL_IMPORTADO = True; logging.info("Módulo 'painel' importado.")
except ImportError as e:
    logging.warning(f"Painel não encontrado: {e}. Usando placeholders."); PAINEL_IMPORTADO = False
    # Placeholders Corrigidos
    def criar_tabela_tokens(): logging.info("Placeholder: Criar tabela tokens")
    def inserir_token(n,t,d): logging.info(f"Placeholder: Inserir token {n}/{t}"); return f"fake_token_{n}"
    def listar_tokens(): logging.info("Placeholder: Listar tokens"); return []
    def excluir_token(tok): logging.info(f"Placeholder: Excluir token {tok}")
    def criar_tabela_chat_history(): logging.info("Placeholder: Criar tabela chat")
    def add_chat_message(ut, r, c): logging.info(f"Placeholder: Add chat msg {ut[:8]} R:{r}"); return True
    def get_chat_history(ut, lim): logging.info(f"Placeholder: Get chat hist {ut[:8]}"); return []

# Importa pytz (com fallback corrigido)
try:
    # Renomeia para evitar conflito com datetime.timezone
    from pytz import timezone as pytz_timezone
    PYTZ_IMPORTADO = True
except ImportError:
    logging.warning("pytz não encontrado."); PYTZ_IMPORTADO = False
    # Não precisamos mais do placeholder class timezone aqui, pois importamos de datetime

# Configuração do App Flask
app = Flask(__name__)
app.secret_key = os.getenv("PAINEL_SENHA", "fallback-key")
if app.secret_key == "fallback-key": logging.warning("PAINEL_SENHA não definida!")

# Configurações da IA
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# ***** MODELO ATUALIZADO DE VOLTA PARA DEEPSEEK *****
AI_MODEL = "deepseek/deepseek-chat" # <<< Usando Deepseek conforme solicitado
# ***** FIM MODELO *****
logging.info(f"Usando modelo de IA: {AI_MODEL}")

# Ler SYSTEM_PROMPT do arquivo
SYSTEM_PROMPT_FILE = "system_prompt.txt"; SYSTEM_PROMPT = "Assistente."
try:
    with open(SYSTEM_PROMPT_FILE,'r',encoding='utf-8') as f: SYSTEM_PROMPT = f.read().strip()
    if SYSTEM_PROMPT and SYSTEM_PROMPT != "Assistente.": logging.info(f"Prompt OK de '{SYSTEM_PROMPT_FILE}'.")
    else: logging.warning(f"Usando prompt padrão.")
except Exception as e: logging.error(f"Erro lendo '{SYSTEM_PROMPT_FILE}': {e}", exc_info=True)
if not OPENROUTER_API_KEY: logging.error("FATAL: OPENROUTER_API_KEY não carregada!")

# Criação Tabelas
try:
    if PAINEL_IMPORTADO: criar_tabela_tokens(); criar_tabela_chat_history()
except Exception as e: logging.error(f"Erro ao criar tabelas: {e}", exc_info=True)

# --- Função Auxiliar API OpenRouter (Corrigida e com Temperatura) ---
def get_ai_response(messages_to_send: list) -> str:
    if not OPENROUTER_API_KEY: raise ValueError("Chave API não configurada.")
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json", "HTTP-Referer": request.url_root if request else "http://localhost:5000", "X-Title": "Dra Ana App"}
    payload = {
        "model": AI_MODEL, # Usa a variável definida acima (DeepSeek agora)
        "messages": messages_to_send,
        "temperature": 0.9, # Mantendo a temperatura
    }
    logging.info(f"Enviando {len(messages_to_send)} msgs para {AI_MODEL} com temp=0.9")
    try: logging.debug(f"Payload (parcial): {json.dumps(payload, ensure_ascii=False)[:500]}...")
    except Exception: logging.debug("Nao logou payload json.")
    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=45); response.raise_for_status()
        api_result=response.json();
        if isinstance(api_result, dict) and 'choices' in api_result and api_result['choices'] and isinstance(api_result['choices'][0], dict) and 'message' in api_result['choices'][0] and isinstance(api_result['choices'][0]['message'], dict) and 'content' in api_result['choices'][0]['message']:
            ai_content = api_result['choices'][0]['message']['content']; logging.info(f"Resposta OK: {ai_content[:100]}..."); return ai_content.strip() if isinstance(ai_content, str) else str(ai_content)
        else: logging.error(f"Resposta API inesperada: {api_result}"); raise ValueError("Resposta API inesperada.")
    except requests.exceptions.Timeout: logging.error("Timeout API."); raise TimeoutError("IA demorou.")
    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code; logging.error(f"Erro HTTP API: {status_code} - {http_err.response.text}")
        if status_code == 401: raise PermissionError("Erro auth API.")
        elif status_code == 402: raise ConnectionRefusedError("Créditos/Limite API.")
        elif status_code == 429: raise ConnectionRefusedError("Limite taxa API.")
        else: raise ConnectionError(f"Erro API ({status_code}).")
    except requests.exceptions.RequestException as e: logging.error(f"Erro rede API: {e}"); raise ConnectionError("Erro rede IA.")
    except Exception as e: logging.exception("Erro inesperado resposta IA."); raise ValueError("Erro processar resposta IA.")

# --- Rotas (Completas e Corrigidas) ---
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
        dias=7 # Idealmente ler do env: int(os.getenv("DEFAULT_TRIAL_DAYS", 7))
        try:
            if PAINEL_IMPORTADO: token=inserir_token(nome,telefone,dias);
            else: logging.warning("Simulando token."); token=f"fake_{nome}"
            if token and isinstance(token, str): session['acesso_concluido']=True; session['user_token']=token; logging.info(f"Acesso OK: {nome}/{telefone}, T:{token[:8]}..."); return redirect(url_for('dra_ana_route'))
            elif token is False: logging.warning(f"Tel duplicado: {telefone}"); return render_template("formulario_acesso.html",sucesso=False,erro="Telefone já cadastrado."), 409
            else: return render_template("formulario_acesso.html",sucesso=False,erro="Erro interno ao criar acesso."), 500
        except Exception as e: logging.error(f"Erro rota /acesso POST: {e}",exc_info=True); return render_template("formulario_acesso.html",sucesso=False,erro="Erro processar acesso."),500
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
    token_gerado_info=None; erro_painel="" # Correção inicialização
    if request.method == "POST": # Lógica para CRIAR token via painel
        # ATENÇÃO: Precisa de campos 'nome_painel' e 'telefone_painel' no form de painel.html
        nome_input = request.form.get("nome_painel", "Usuário Painel") # Pega nome do form
        telefone_input = request.form.get("telefone_painel", None) # Pega telefone
        try:
            dias_str=request.form.get("dias_validade",'7'); assert dias_str.isdigit() and int(dias_str)>0
            dias=int(dias_str)
            if not telefone_input: raise ValueError("Telefone é obrigatório para criar token.")

            if PAINEL_IMPORTADO:
                 token_gerado_info=inserir_token(nome=nome_input, telefone=telefone_input, dias_validade=dias);
                 if token_gerado_info is False: erro_painel = "Telefone já existe."
                 elif token_gerado_info is None: erro_painel = "Erro ao gerar token."
                 else: logging.info(f"Admin gerou token {nome_input}/{telefone_input[:5]}.../{dias}d.") # token_gerado_info é o token str
            else: erro_painel="Painel não importado."
        except(ValueError,AssertionError) as ve: erro_painel=f"Dados inválidos: {ve}"; logging.warning(erro_painel)
        except Exception as e: logging.exception("Erro gerar token painel."); erro_painel="Erro inesperado."

    # Lógica para LISTAR tokens (precisa ajustar listar_tokens e template)
    tokens=[];
    try:
        if PAINEL_IMPORTADO: tokens=listar_tokens() # << AINDA PRECISA AJUSTAR listar_tokens no painel/__init__.py
        else: msg_e="Painel não importado."; erro_painel+=(" "+msg_e if erro_painel else msg_e)
    except Exception as e: logging.exception("Erro listar tokens."); msg_e="Erro listar tokens."; erro_painel+=(" "+msg_e if erro_painel else msg_e)

    now_tz=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'); # Usa UTC por padrão
    if PYTZ_IMPORTADO:
        try: now_tz=datetime.now(pytz_timezone("America/Sao_Paulo")).strftime('%Y-%m-%d %H:%M:%S %Z%z') # Usa pytz_timezone
        except Exception as e: logging.warning(f"Erro timezone: {e}. Usando UTC.")

    token_real_gerado = token_gerado_info if isinstance(token_gerado_info, str) else None
    return render_template("painel.html",token_gerado=token_real_gerado,tokens=tokens,now=now_tz,erro=erro_painel) # Ajustado token_gerado

@app.route("/excluir_token", methods=["POST"])
def excluir_token_route():
    if not session.get("autenticado"): return redirect(url_for("login"))
    token=request.form.get("token")
    if token:
        try:
            if PAINEL_IMPORTADO: excluir_token(token);
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