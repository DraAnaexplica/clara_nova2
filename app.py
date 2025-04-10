# app.py (VERSÃO ATUALIZADA - PÓS Passo 2.2)

import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from dotenv import load_dotenv
import logging
from datetime import datetime
import json

# Configuração de Logging (mantido)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carrega variáveis de ambiente do .env (mantido)
load_dotenv_success = load_dotenv(override=True, verbose=True)
logging.info(f"Arquivo .env carregado com sucesso? {load_dotenv_success}")

# 👇👇👇 IMPORTAÇÃO MODIFICADA ABAIXO (adicionado verificar_token_valido) 👇👇👇
try:
    from painel import ( 
        criar_tabela_tokens, inserir_token, listar_tokens, excluir_token, 
        verificar_token_valido, # <--- ADICIONADO AQUI
        criar_tabela_chat_history, add_chat_message, get_chat_history 
    )
    PAINEL_IMPORTADO = True
    logging.info("Módulo 'painel' (com verificar_token_valido) e funções de chat importados com sucesso.")
except ImportError as e:
    logging.warning(f"Módulo 'painel' não encontrado ou com erro: {e}. Usando placeholders.")
    PAINEL_IMPORTADO = False
    # Placeholders 
    def criar_tabela_tokens(): logging.info("Placeholder: Criar tabela tokens")
    def inserir_token(nome, telefone, dias): logging.info(f"Placeholder: Inserir token {nome}/{telefone}"); return f"fake_token_{nome}" 
    def listar_tokens(): logging.info("Placeholder: Listar tokens"); return []
    def excluir_token(tok): logging.info(f"Placeholder: Excluir token {tok}")
    # Placeholder para a nova função
    def verificar_token_valido(tok): logging.warning(f"Placeholder: Verificando token {tok[:8]}..."); return True # Assume válido no placeholder
    def criar_tabela_chat_history(): logging.info("Placeholder: Criar tabela chat")
    def add_chat_message(ut, r, c): logging.info(f"Placeholder: Add chat msg {ut[:8]} R:{r}"); return True
    def get_chat_history(ut, lim): logging.info(f"Placeholder: Get chat hist {ut[:8]}"); return []
# 👆👆👆 IMPORTAÇÃO MODIFICADA ACIMA 👆👆👆

# Importa pytz (mantido)
try:
    from pytz import timezone
    PYTZ_IMPORTADO = True
except ImportError:
    # ... (fallback mantido) ...
    logging.warning("Biblioteca 'pytz' não encontrada. Usando UTC.")
    PYTZ_IMPORTADO = False
    class timezone:
        def __init__(self, tz_name):
            pass

# Configuração do App Flask (mantido)
app = Flask(__name__)
app.secret_key = os.getenv("PAINEL_SENHA", "configure-uma-chave-secreta-forte-no-env")
# ... (restante da configuração mantido) ...
if app.secret_key == "configure-uma-chave-secreta-forte-no-env": logging.warning("PAINEL_SENHA não definida!")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
AI_MODEL = "deepseek/deepseek-chat-v3-0324"
logging.info(f"Usando modelo de IA: {AI_MODEL}")
SYSTEM_PROMPT_FILE = "system_prompt.txt"; SYSTEM_PROMPT = "Assistente."
try:
    with open(SYSTEM_PROMPT_FILE, 'r', encoding='utf-8') as f: SYSTEM_PROMPT = f.read().strip()
    if SYSTEM_PROMPT and SYSTEM_PROMPT != "Assistente.": logging.info(f"Prompt OK de '{SYSTEM_PROMPT_FILE}'.")
    else: logging.warning(f"Usando prompt padrão.")
except Exception as e: logging.error(f"Erro lendo '{SYSTEM_PROMPT_FILE}': {e}", exc_info=True)
if not OPENROUTER_API_KEY: logging.error("FATAL: OPENROUTER_API_KEY não carregada!")

# Criação Tabelas (mantido)
try:
    if PAINEL_IMPORTADO: criar_tabela_tokens(); criar_tabela_chat_history()
except Exception as e: logging.error(f"Erro ao criar tabelas: {e}", exc_info=True)

# --- Função Auxiliar API OpenRouter (mantido) ---
def get_ai_response(messages_to_send: list) -> str:
    # ... (código original mantido) ...
    if not OPENROUTER_API_KEY: raise ValueError("Chave API não configurada.")
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json", "HTTP-Referer": request.url_root if request else "http://localhost:5000", "X-Title": "Dra Ana App"}
    payload = {"model": AI_MODEL, "messages": messages_to_send, "temperature": 0.9}
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
        # ... (tratamento de erro mantido) ...
        status_code = http_err.response.status_code
        logging.error(f"Erro HTTP API: {status_code} - {http_err.response.text}")
        if status_code == 401: raise PermissionError("Erro auth API.")
        elif status_code == 402: raise ConnectionRefusedError("Créditos/Limite API.")
        elif status_code == 429: raise ConnectionRefusedError("Limite taxa API.")
        else: raise ConnectionError(f"Erro API ({status_code}).")
    except requests.exceptions.RequestException as e: logging.error(f"Erro rede API: {e}"); raise ConnectionError("Erro rede IA.")
    except Exception as e: logging.exception("Erro inesperado resposta IA."); raise ValueError("Erro processar resposta IA.")


# --- Rotas ---

@app.route("/") # Mantido
def index(): return redirect(url_for("instalar"))

@app.route("/instalar") # Mantido
def instalar():
    # ... (código original mantido) ...
    if session.get('acesso_concluido') and session.get('user_token'): return redirect(url_for('dra_ana_route'))
    return render_template("formulario_acesso.html", exibir_instalador=True)

@app.route("/acesso", methods=["GET", "POST"]) # Mantido (Pós Passo 1.3)
def acesso_usuario():
    # ... (código original mantido - já ajustado no passo 1.3) ...
    if request.method == "POST":
        nome = request.form.get("nome")
        telefone = request.form.get("telefone")
        if not nome or not telefone:
            return render_template("formulario_acesso.html", sucesso=False, erro="Nome e telefone são obrigatórios."), 400
        dias = 7 
        try:
            if PAINEL_IMPORTADO:
                token_gerado = inserir_token(nome=nome, telefone=telefone, dias_validade=dias)
            else:
                logging.warning("Simulando token (painel não importado).")
                token_gerado = f"fake_{nome}_{telefone}" 
            if token_gerado:
                session['acesso_concluido'] = True
                session['user_token'] = token_gerado 
                logging.info(f"Acesso OK: Nome='{nome}', Tel='***{telefone[-4:]}', Token='{token_gerado[:8]}...'")
                return redirect(url_for('dra_ana_route'))
            else:
                logging.warning(f"Falha ao gerar token para Nome='{nome}', Tel='***{telefone[-4:]}'. Telefone pode já existir.")
                return render_template("formulario_acesso.html", sucesso=False, erro="Telefone já cadastrado ou erro ao gerar acesso. Tente novamente ou contate o suporte."), 400
        except Exception as e:
            logging.error(f"Erro crítico ao processar acesso para Nome='{nome}', Tel='***{telefone[-4:]}': {e}", exc_info=True)
            return render_template("formulario_acesso.html", sucesso=False, erro="Erro interno ao processar seu acesso. Tente mais tarde."), 500
    if session.get('acesso_concluido') and session.get('user_token'):
        return redirect(url_for('dra_ana_route'))
    else:
        session.pop('acesso_concluido', None); session.pop('user_token', None); session.modified=True
        return render_template("formulario_acesso.html", sucesso=False)


# 👇👇👇 ROTA MODIFICADA ABAIXO (Passo 2.2) 👇👇👇
@app.route("/dra-ana")
def dra_ana_route():
    user_token = session.get('user_token')
    acesso_ok = session.get('acesso_concluido')

    # 1. Verifica se tem token e flag de acesso na sessão
    if not acesso_ok or not user_token:
        logging.debug("Tentativa de acesso a /dra-ana sem token/flag na sessão.")
        return redirect(url_for('instalar')) # Redireciona se não houver info na sessão

    # 2. Verifica se o token da sessão é VÁLIDO no banco de dados
    if PAINEL_IMPORTADO: # Só faz a verificação se o painel foi importado corretamente
        if not verificar_token_valido(user_token):
            logging.warning(f"Acesso negado a /dra-ana: Token inválido ou expirado ({user_token[:8]}...). Removendo da sessão.")
            # Limpa a sessão se o token for inválido
            session.pop('acesso_concluido', None)
            session.pop('user_token', None)
            session.modified = True
            # Redireciona para a página inicial/acesso (ou uma página de 'expirado' no futuro)
            return redirect(url_for('instalar')) 
            # TODO: No futuro (Passo 4.3), redirecionar para uma rota /expirado aqui

    # Se passou pelas verificações, renderiza o chat
    logging.debug(f"Acesso permitido a /dra-ana para token {user_token[:8]}...")
    return render_template("chat.html")
# 👆👆👆 ROTA MODIFICADA ACIMA 👆👆👆


# 👇👇👇 ROTA MODIFICADA ABAIXO (Passo 2.2) 👇👇👆
@app.route("/chat", methods=["POST"])
def chat_endpoint():
    user_token = session.get('user_token')
    acesso_ok = session.get('acesso_concluido')

    # 1. Verifica se tem token e flag na sessão
    if not acesso_ok or not user_token:
        logging.warning("API /chat: Acesso negado (sem token/flag na sessão).")
        return jsonify({"error": "Sessão inválida ou inexistente"}), 403

    # 2. Verifica se o token da sessão é VÁLIDO no banco de dados
    is_valid_token = True # Assume válido se não puder verificar
    if PAINEL_IMPORTADO:
        is_valid_token = verificar_token_valido(user_token)

    if not is_valid_token:
        logging.warning(f"API /chat: Acesso negado (Token inválido ou expirado: {user_token[:8]}...). Removendo da sessão.")
        # Limpa a sessão se o token for inválido
        session.pop('acesso_concluido', None)
        session.pop('user_token', None)
        session.modified = True
        # Retorna erro 403 (Proibido) para a API
        return jsonify({"error": "Token inválido ou expirado"}), 403

    # --- Se o token for válido, continua o processamento da mensagem ---
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
            
        except(ValueError,ConnectionError,PermissionError,TimeoutError,ConnectionRefusedError) as e: 
            error_message=str(e); 
            sc=503 if isinstance(e,(TimeoutError,ConnectionError,ConnectionRefusedError)) else 401 if isinstance(e,PermissionError) else 500; 
            logging.error(f"API /chat: Erro ao chamar IA para token {user_token[:8]}...: {error_message}")
            return jsonify({"error":f"Erro IA: {error_message}"}), sc
        except Exception as e: 
            logging.exception(f"API /chat: Erro inesperado no call get_ai_response para token {user_token[:8]}..."); 
            return jsonify({"error": "Erro interno IA."}), 500
            
    except Exception as e: 
        logging.exception(f"API /chat: Erro geral no processamento para token {user_token[:8]}..."); 
        return jsonify({"error": "Erro interno servidor."}), 500
# 👆👆👆 ROTA MODIFICADA ACIMA 👆👆👆

# --- Rotas do Painel Admin (mantidas como pós Passo 1.3) ---
@app.route("/login", methods=["GET", "POST"]) 
def login():
    # ... (código mantido) ...
    if request.method == "POST":
        senha = request.form.get("senha"); sp = os.getenv("PAINEL_SENHA")
        if not sp: logging.error("PAINEL_SENHA não config!"); return "Erro config.", 500
        if senha == sp: session["autenticado"] = True; logging.info("Admin auth OK."); return redirect(url_for("painel"))
        else: logging.warning("Login painel falhou."); return "❌ Senha incorreta", 401
    return'''<form method="POST"><label>Senha Painel: <input type="password" name="senha" required></label><button type="submit">Entrar</button></form>'''

@app.route("/logout") 
def logout():
    # ... (código mantido) ...
    admin_antes=session.pop("autenticado",None);session.modified=True
    if admin_antes: logging.info("Admin deslogado.")
    return redirect(url_for("login"))

@app.route("/painel", methods=["GET", "POST"]) 
def painel():
    # ... (código mantido - já ajustado no passo 1.3) ...
    if not session.get("autenticado"): return redirect(url_for("login"))
    token_gerado_str = None 
    erro_painel = ""
    if request.method == "POST":
        nome_novo_token = request.form.get("nome")
        telefone_novo_token = request.form.get("telefone")
        dias_str = request.form.get("dias_validade", '7') 
        if not nome_novo_token or not telefone_novo_token:
            erro_painel = "Nome e telefone são obrigatórios para criar token."
        elif not dias_str.isdigit() or int(dias_str) <= 0:
             erro_painel = "Número de dias de validade inválido."
        else:
            dias = int(dias_str)
            try:
                if PAINEL_IMPORTADO:
                    resultado_insert = inserir_token(nome=nome_novo_token, telefone=telefone_novo_token, dias_validade=dias)
                    if resultado_insert:
                        token_gerado_str = resultado_insert 
                        logging.info(f"Admin gerou token: Nome='{nome_novo_token}', Tel='***{telefone_novo_token[-4:]}', Dias={dias}, Token='{token_gerado_str[:8]}...'")
                    else:
                        erro_painel = "Erro ao gerar token (verifique se o telefone já existe)."
                        logging.warning(f"Admin falhou ao gerar token: Nome='{nome_novo_token}', Tel='***{telefone_novo_token[-4:]}'. Telefone duplicado ou erro interno.")
                else:
                     erro_painel="Painel não importado, impossível gerar token real."
            except Exception as e:
                logging.exception("Erro inesperado ao gerar token pelo painel.")
                erro_painel="Erro inesperado no servidor ao gerar token."
    tokens = []
    try:
        if PAINEL_IMPORTADO:
            tokens = listar_tokens()
        else:
             msg_e="Painel não importado, não pode listar tokens."; erro_painel+=(" "+msg_e if erro_painel else msg_e)
    except Exception as e:
        logging.exception("Erro ao listar tokens para o painel.")
        msg_e="Erro ao buscar lista de tokens."; erro_painel+=(" "+msg_e if erro_painel else msg_e)
    now_tz = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC');
    if PYTZ_IMPORTADO:
        try: now_tz=datetime.now(timezone("America/Sao_Paulo")).strftime('%Y-%m-%d %H:%M:%S %Z%z')
        except Exception as e: logging.warning(f"Erro timezone: {e}. Usando UTC.")
    return render_template("painel.html",
                           token_gerado=token_gerado_str, 
                           tokens=tokens, 
                           now=now_tz,
                           erro=erro_painel)

@app.route("/excluir_token", methods=["POST"]) 
def excluir_token_route():
    # ... (código mantido) ...
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
    # ... (código mantido) ...
    session.pop('acesso_concluido',None); session.pop('user_token',None); session.modified=True
    logging.info("Sessão de acesso resetada.")
    return"Sessão de acesso e histórico de chat resetados. <a href='/'>Voltar ao início</a>"

# Bloco main (mantido)
if __name__ == "__main__":
    port=int(os.environ.get('PORT',5000)); debug_mode=os.environ.get('FLASK_DEBUG','False').lower() in ['true','1','t']
    logging.info(f"Iniciando app em host=0.0.0.0, port={port}, debug={debug_mode}")
    app.run(debug=debug_mode,host='0.0.0.0',port=port)