# app.py (VERSÃO COMPLETA - CORREÇÃO com Modificações)

import os
import requests
# Importação do Flash adicionada
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash 
from dotenv import load_dotenv
import logging
from datetime import datetime
import json

# Configuração de Logging 
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carrega variáveis de ambiente do .env 
load_dotenv_success = load_dotenv(override=True, verbose=True)
logging.info(f"Arquivo .env carregado com sucesso? {load_dotenv_success}")

# --- Modificação 1: Adicionar Importação do buscar_token_ativo_por_telefone ---
try:
    from painel import ( 
        criar_tabela_tokens, inserir_token, listar_tokens, excluir_token, 
        verificar_token_valido, 
        atualizar_validade_token, 
        buscar_token_ativo_por_telefone,  # <--- LINHA ADICIONADA/GARANTIDA
        criar_tabela_chat_history, add_chat_message, get_chat_history 
    )
    PAINEL_IMPORTADO = True
    logging.info("Módulo 'painel' (com buscar_token) e chat importados com sucesso.")
except ImportError as e:
    logging.warning(f"Módulo 'painel' não encontrado ou com erro: {e}. Usando placeholders.")
    PAINEL_IMPORTADO = False
    # Placeholders 
    def criar_tabela_tokens(): 
        logging.info("Placeholder: Criar tabela tokens")
    def inserir_token(nome, telefone, dias): 
        logging.info(f"Placeholder: Inserir token {nome}/{telefone}")
        return f"fake_token_{nome}"
    def listar_tokens(): 
        logging.info("Placeholder: Listar tokens")
        return []
    def excluir_token(tok): 
        logging.info(f"Placeholder: Excluir token {tok}")
    def verificar_token_valido(tok): 
        logging.warning(f"Placeholder: Verificando token {tok[:8]}...")
        return True
    def atualizar_validade_token(tok, dias): 
        logging.warning(f"Placeholder: Atualizando token {tok[:8]} +{dias}d")
        return True
    def buscar_token_ativo_por_telefone(telefone_a_buscar): 
        logging.warning(f"Placeholder: Buscando T p/ tel ***{telefone_a_buscar[-4:]}")
        return None
    def criar_tabela_chat_history(): 
        logging.info("Placeholder: Criar tabela chat")
    def add_chat_message(ut, r, c): 
        logging.info(f"Placeholder: Add chat msg {ut[:8]} R:{r}")
        return True
    def get_chat_history(ut, lim): 
        logging.info(f"Placeholder: Get chat hist {ut[:8]}")
        return []

# Importa pytz 
try:
    # Tenta importar o pytz real
    from pytz import timezone
    PYTZ_IMPORTADO = True
    logging.info("Biblioteca 'pytz' importada com sucesso.")
except ImportError:
    # 👇👇 BLOCO CORRIGIDO ABAIXO 👇👇
    logging.warning("Biblioteca 'pytz' não encontrada. Usando placeholder UTC.")
    PYTZ_IMPORTADO = False
    # Define uma classe placeholder simples que não faz nada
    class timezone:
        def __init__(self, tz_name):
            logging.debug(f"Usando placeholder timezone para: {tz_name}")
    # 👆👆 BLOCO CORRIGIDO ACIMA 👆👆

# Configuração do App Flask 
app = Flask(__name__)
app.secret_key = os.getenv("PAINEL_SENHA", "configure-uma-chave-secreta-forte-no-env")
if app.secret_key == "configure-uma-chave-secreta-forte-no-env":
    logging.warning("PAINEL_SENHA não definida!")

# Configurações da IA 
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
AI_MODEL = "openai/chatgpt-4o-latest" 
logging.info(f"Usando modelo de IA: {AI_MODEL}")

# Ler SYSTEM_PROMPT do arquivo 
SYSTEM_PROMPT_FILE = "system_prompt.txt"
SYSTEM_PROMPT = "Assistente."
try:
    with open(SYSTEM_PROMPT_FILE, 'r', encoding='utf-8') as f:
        SYSTEM_PROMPT = f.read().strip()
    if SYSTEM_PROMPT and SYSTEM_PROMPT != "Assistente.":
        logging.info(f"Prompt OK de '{SYSTEM_PROMPT_FILE}'.")
    else:
        logging.warning(f"Usando prompt padrão.")
except Exception as e:
    logging.error(f"Erro lendo '{SYSTEM_PROMPT_FILE}': {e}", exc_info=True)
if not OPENROUTER_API_KEY:
    logging.error("FATAL: OPENROUTER_API_KEY não carregada!")

# Criação Tabelas 
try:
    if PAINEL_IMPORTADO:
        criar_tabela_tokens()
        criar_tabela_chat_history()
except Exception as e:
    logging.error(f"Erro ao criar tabelas: {e}", exc_info=True)

# --- Função Auxiliar API OpenRouter ---
def get_ai_response(messages_to_send: list) -> str:
    """Envia mensagens para a API OpenRouter e retorna a resposta da IA."""
    if not OPENROUTER_API_KEY:
        raise ValueError("Chave API não configurada.")
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}", 
        "Content-Type": "application/json", 
        "HTTP-Referer": request.url_root if request else "http://localhost:5000", 
        "X-Title": "Dra Ana App" 
    }
    payload = {
        "model": AI_MODEL, 
        "messages": messages_to_send, 
        "temperature": 0.9 
    } 
    logging.info(f"Enviando {len(messages_to_send)} msgs para {AI_MODEL} com temp=0.9")
    try: 
        logging.debug(f"Payload (parcial): {json.dumps(payload, ensure_ascii=False)[:500]}...")
    except Exception: 
        logging.debug("Nao logou payload json.")
        
    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=45)
        response.raise_for_status() 
        api_result = response.json()
        if (isinstance(api_result, dict) and 'choices' in api_result and 
            api_result['choices'] and isinstance(api_result['choices'][0], dict) and 
            'message' in api_result['choices'][0] and 
            isinstance(api_result['choices'][0]['message'], dict) and 
            'content' in api_result['choices'][0]['message']):
            ai_content = api_result['choices'][0]['message']['content']
            logging.info(f"Resposta OK da IA: {ai_content[:100]}...")
            return ai_content.strip() if isinstance(ai_content, str) else str(ai_content)
        else:
            logging.error(f"Resposta da API OpenRouter inesperada: {api_result}")
            raise ValueError("Resposta da API inesperada.")
    except requests.exceptions.Timeout:
        logging.error("Timeout ao conectar com a API OpenRouter.")
        raise TimeoutError("A IA demorou muito para responder.")
    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code
        logging.error(f"Erro HTTP da API OpenRouter: {status_code} - {http_err.response.text}")
        if status_code == 401:
            raise PermissionError("Erro de autenticação com a API.")
        elif status_code == 402:
            raise ConnectionRefusedError("Problema de crédito ou limite excedido na API.")
        elif status_code == 429:
            raise ConnectionRefusedError("Limite de taxa (rate limit) da API excedido.")
        else:
            raise ConnectionError(f"Erro na comunicação com a API ({status_code}).")
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro de rede ao conectar com a API OpenRouter: {e}")
        raise ConnectionError("Erro de rede ao conectar com a IA.")
    except Exception as e:
        logging.exception("Erro inesperado ao processar resposta da IA.")
        raise ValueError("Erro ao processar a resposta da IA.")

# --- Rotas ---

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
    """Processa o formulário de acesso inicial."""
    if request.method == "POST":
        nome = request.form.get("nome")
        telefone = request.form.get("telefone")
        if not nome or not telefone:
            return render_template("formulario_acesso.html", sucesso=False, erro="Nome e telefone são obrigatórios."), 400
        dias = 7 
        
        # --- Modificação 2: Substituir bloco try/except na rota /acesso ---
        token_final_sessao = None  # Guarda o token que irá para a sessão

        # Bloco try/except para chamar as funções do painel
        try:
            if PAINEL_IMPORTADO:
                # 1. Tenta INSERIR (cadastrar) novo token
                logging.debug(f"Tentando inserir token para Tel='***{telefone[-4:]}'")
                token_gerado = inserir_token(nome=nome, telefone=telefone, dias_validade=dias)

                if token_gerado:
                    # Sucesso na inserção (novo usuário)
                    token_final_sessao = token_gerado
                    logging.info(f"Novo Acesso OK: N='{nome}', T='***{telefone[-4:]}', Token='{token_final_sessao[:8]}...'")
                else:
                    # Inserção falhou (provavelmente telefone duplicado)
                    logging.warning(f"Falha ao inserir token N='{nome}', T='***{telefone[-4:]}'. Buscando token ativo...")
                    # 2. Tenta BUSCAR token ativo existente para o telefone
                    #    (Usa a função buscar_token_ativo_por_telefone importada)
                    token_existente = buscar_token_ativo_por_telefone(telefone_a_buscar=telefone)

                    if token_existente:
                        # Sucesso na busca (usuário existente com token ativo) -> LOGIN
                        token_final_sessao = token_existente
                        logging.info(f"Re-Acesso OK (token existente): T='***{telefone[-4:]}', Token='{token_final_sessao[:8]}...'")
                    else:
                        # Falha na busca (tel existe mas token inativo/expirado/erro)
                        logging.warning(f"Nenhum token ativo para T='***{telefone[-4:]}' após falha inserção.")
                        return render_template("formulario_acesso.html", sucesso=False, erro="Seu telefone já está cadastrado, mas o acesso está inativo ou expirou. Contate o suporte."), 400
            else:
                # Se PAINEL_IMPORTADO for False (usando placeholders)
                logging.warning("Simulando login (painel não importado).")
                token_final_sessao = f"fake_login_{nome}_{telefone[-4:]}"
            
            # 3. Se temos um token (novo ou existente), salva na sessão e redireciona
            if token_final_sessao:
                session['acesso_concluido'] = True
                session['user_token'] = token_final_sessao 
                return redirect(url_for('dra_ana_route'))
            else:
                logging.error(f"Erro inesperado no fluxo acesso/login T='***{telefone[-4:]}'")
                return render_template("formulario_acesso.html", sucesso=False, erro="Erro inesperado no acesso."), 500

        except Exception as e:
            logging.error(f"Erro crítico acesso/login N='{nome}', T='***{telefone[-4:]}': {e}", exc_info=True)
            return render_template("formulario_acesso.html", sucesso=False, erro="Erro interno. Tente mais tarde."), 500

    # Bloco GET permanece inalterado:
    if session.get('acesso_concluido') and session.get('user_token'):
        return redirect(url_for('dra_ana_route'))
    else:
        session.pop('acesso_concluido', None)
        session.pop('user_token', None)
        session.modified = True
        return render_template("formulario_acesso.html", sucesso=False)

@app.route("/dra-ana") 
def dra_ana_route():
    """Página principal do chat."""
    user_token = session.get('user_token')
    acesso_ok = session.get('acesso_concluido')
    if not acesso_ok or not user_token:
        logging.debug("Tentativa de acesso a /dra-ana sem token/flag na sessão.")
        return redirect(url_for('instalar'))
    if PAINEL_IMPORTADO:
        if not verificar_token_valido(user_token):
            logging.warning(f"Acesso negado a /dra-ana: Token inválido ou expirado ({user_token[:8]}...). Removendo da sessão.")
            session.pop('acesso_concluido', None)
            session.pop('user_token', None)
            session.modified = True
            flash("Seu acesso expirou ou é inválido. Por favor, acesse novamente.", "warning")
            return redirect(url_for('instalar'))
    logging.debug(f"Acesso permitido a /dra-ana para token {user_token[:8]}...")
    return render_template("chat.html")

@app.route("/chat", methods=["POST"]) 
def chat_endpoint():
    """Endpoint da API para receber e responder mensagens do chat."""
    user_token = session.get('user_token')
    acesso_ok = session.get('acesso_concluido')
    if not acesso_ok or not user_token:
        logging.warning("API /chat: Acesso negado (sem token/flag na sessão).")
        return jsonify({"error": "Sessão inválida ou inexistente"}), 403
    is_valid_token = True 
    if PAINEL_IMPORTADO:
        is_valid_token = verificar_token_valido(user_token)
    if not is_valid_token:
        logging.warning(f"API /chat: Acesso negado (Token inválido ou expirado: {user_token[:8]}...). Removendo da sessão.")
        session.pop('acesso_concluido', None)
        session.pop('user_token', None)
        session.modified = True
        return jsonify({"error": "Token inválido ou expirado"}), 403
    try:
        data = request.get_json()
        if not data or "mensagem" not in data:
            logging.warning(f"API /chat: Payload inválido ou sem 'mensagem'. T:{user_token[:8]}")
            return jsonify({"error": "Requisição inválida"}), 400
        user_message = data.get("mensagem")
        if not isinstance(user_message, str) or not user_message.strip():
            logging.warning(f"API /chat: Mensagem vazia recebida. T:{user_token[:8]}")
            return jsonify({"error": "Mensagem não pode ser vazia"}), 400
        logging.info(f"Msg Recebida (T:{user_token[:8]}): {user_message[:100]}...")
        if PAINEL_IMPORTADO:
            telefone = session.get('telefone') or 'indefinido'
            add_chat_message(telefone, 'user', user_message)
        else:
            logging.warning("Placeholder: Não salvando msg user.")
        chat_history = []
        if PAINEL_IMPORTADO:
            chat_history = get_chat_history(user_token, limit=20)
        else:
            logging.warning("Placeholder: Não buscando histórico.")
        messages_to_send = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_history
        try:
            ai_response = get_ai_response(messages_to_send)
            if PAINEL_IMPORTADO:
                add_chat_message(telefone, 'assistant', ai_response)
            else:
                logging.warning("Placeholder: Não salvando msg assistant.")
            return jsonify({"response": ai_response})
        except (ValueError, ConnectionError, PermissionError, TimeoutError, ConnectionRefusedError) as e:
            error_message = str(e)
            status_code = 503 if isinstance(e, (TimeoutError, ConnectionError, ConnectionRefusedError)) else \
                          401 if isinstance(e, PermissionError) else 500
            logging.error(f"API /chat: Erro ao chamar IA para T:{user_token[:8]}...: {error_message}")
            return jsonify({"error": f"Erro ao comunicar com a IA: {error_message}"}), status_code
        except Exception as e:
            logging.exception(f"API /chat: Erro inesperado no call get_ai_response T:{user_token[:8]}...")
            return jsonify({"error": "Erro interno ao processar na IA."}), 500
    except Exception as e:
        logging.exception(f"API /chat: Erro geral no processamento T:{user_token[:8]}...")
        return jsonify({"error": "Erro interno no servidor."}), 500

# --- Rotas do Painel Admin ---

@app.route("/login", methods=["GET", "POST"]) 
def login():
    """Página de login do painel admin."""
    # Adiciona render_template para GET
    if request.method == 'GET':
        return render_template('login.html')  # Supõe que existe um login.html

    # Lógica POST continua a mesma
    senha_digitada = request.form.get("senha")
    senha_painel = os.getenv("PAINEL_SENHA")
    if not senha_painel:
        logging.error("PAINEL_SENHA não configurada no ambiente!")
        flash("Erro de configuração interna do servidor.", "danger")
        return render_template("login.html", erro="Erro config."), 500
    if senha_digitada == senha_painel:
        session["autenticado"] = True
        logging.info("Admin autenticado com sucesso.")
        flash("Login realizado com sucesso!", "success")
        return redirect(url_for("painel"))
    else:
        logging.warning("Tentativa de login no painel falhou (senha incorreta).")
        flash("Senha incorreta.", "danger")
        return render_template("login.html", erro="Senha incorreta"), 401

@app.route("/logout") 
def logout():
    """Faz logout do admin."""
    admin_estava_logado = session.pop("autenticado", None)
    session.modified = True 
    if admin_estava_logado:
        logging.info("Admin deslogado.")
        flash("Logout realizado com sucesso.", "info")
    return redirect(url_for("login"))

@app.route("/painel", methods=["GET", "POST"]) 
def painel():
    """Página principal do painel admin."""
    if not session.get("autenticado"):
        return redirect(url_for("login"))

    token_gerado_str = None 
    erro_painel = "" 

    if request.method == "POST":
        # Lógica POST para criar token (já ajustada)
        nome_novo_token = request.form.get("nome")
        telefone_novo_token = request.form.get("telefone")
        dias_str = request.form.get("dias_validade", '7') 
        if not nome_novo_token or not telefone_novo_token:
            flash("Nome e telefone são obrigatórios para criar token.", "danger")
        elif not dias_str.isdigit() or int(dias_str) <= 0:
            flash("Número de dias de validade inválido.", "danger")
        else:
            dias = int(dias_str)
            try:
                if PAINEL_IMPORTADO:
                    resultado_insert = inserir_token(nome=nome_novo_token, telefone=telefone_novo_token, dias_validade=dias)
                    if resultado_insert:
                        token_gerado_str = resultado_insert 
                        flash(f"Token gerado com sucesso para {nome_novo_token}: {token_gerado_str}", "success")
                        logging.info(f"Admin gerou token: N='{nome_novo_token}', T='***{telefone_novo_token[-4:]}', Dias={dias}, T='{token_gerado_str[:8]}...'")
                    else:
                        flash(f"Erro ao gerar token para {nome_novo_token} (verifique se o telefone já existe).", "warning")
                        logging.warning(f"Admin falhou gerar token: N='{nome_novo_token}', T='***{telefone_novo_token[-4:]}'. Duplicado/erro.")
                else:
                    flash("Erro: Módulo do painel não carregado.", "danger")
            except Exception as e:
                logging.exception("Erro inesperado ao gerar token pelo painel.")
                flash("Erro inesperado no servidor ao gerar token.", "danger")
        return redirect(url_for('painel'))  # Redireciona após POST

    # Lógica GET (busca tokens sempre)
    tokens = []
    try:
        if PAINEL_IMPORTADO:
            tokens = listar_tokens()
        else:
            erro_painel = "Painel não importado, não pode listar tokens."
    except Exception as e:
        logging.exception("Erro ao listar tokens para o painel.")
        erro_painel = "Erro ao buscar lista de tokens."

    now_tz = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    if PYTZ_IMPORTADO:
        try: 
            now_tz = datetime.now(timezone("America/Sao_Paulo")).strftime('%Y-%m-%d %H:%M:%S %Z%z')
        except Exception as e: 
            logging.warning(f"Erro timezone: {e}. Usando UTC.")

    return render_template("painel.html",
                           tokens=tokens, 
                           now=now_tz,
                           erro=erro_painel)

@app.route("/excluir_token", methods=["POST"]) 
def excluir_token_route():
    """Processa a exclusão de um token."""
    if not session.get("autenticado"):
        flash("Acesso não autorizado.", "warning")
        return redirect(url_for("login"))
    token_para_excluir = request.form.get("token")
    if token_para_excluir:
        if PAINEL_IMPORTADO:
            try:
                sucesso = excluir_token(token_para_excluir)
                if sucesso:
                    flash(f"Token {token_para_excluir[:8]}... excluído com sucesso!", "success")
                    logging.info(f"Admin excluiu token: {token_para_excluir[:8]}...")
                else:
                    flash(f"Token {token_para_excluir[:8]}... não encontrado para exclusão.", "warning")
                    logging.warning(f"Admin tentou excluir token não encontrado: {token_para_excluir[:8]}...")
            except Exception as e:
                logging.exception(f"Erro ao excluir token {token_para_excluir[:8]}...")
                flash("Erro interno ao tentar excluir token.", "danger")
        else:
            flash("Erro: Módulo do painel não carregado.", "danger")
    else:
        flash("Erro: Nenhum token fornecido para exclusão.", "warning")
        logging.warning("Admin tentou exclusão sem fornecer token.")
    return redirect(url_for("painel"))

@app.route("/atualizar_token", methods=["POST"])
def atualizar_token_route():
    """Recebe a solicitação do painel para atualizar a validade de um token."""
    if not session.get("autenticado"):
        flash("Acesso não autorizado.", "warning")
        return redirect(url_for("login"))
    token_para_atualizar = request.form.get("token")
    dias_para_adicionar_str = request.form.get("dias_adicionar")
    if not token_para_atualizar or not dias_para_adicionar_str:
        flash("Erro: Token ou número de dias não fornecido.", "danger")
        return redirect(url_for("painel"))
    try:
        dias_int = int(dias_para_adicionar_str)
        if dias_int <= 0:
            flash("Erro: Número de dias deve ser positivo.", "danger")
            return redirect(url_for("painel"))
    except ValueError:
        flash("Erro: Número de dias inválido.", "danger")
        return redirect(url_for("painel"))
    if PAINEL_IMPORTADO:
        try:
            sucesso = atualizar_validade_token(token_a_atualizar=token_para_atualizar, dias_a_adicionar=dias_int)
            if sucesso:
                flash(f"Validade do token {token_para_atualizar[:8]}... atualizada com sucesso!", "success")
                logging.info(f"Admin atualizou validade: T:{token_para_atualizar[:8]}... +{dias_int}d")
            else:
                flash(f"Erro: Token {token_para_atualizar[:8]}... não encontrado para atualização.", "warning")
                logging.warning(f"Admin falhou att validade: T:{token_para_atualizar[:8]}... não encontrado.")
        except Exception as e:
            logging.exception(f"Erro inesperado ao chamar atualizar_validade_token T:{token_para_atualizar[:8]}...")
            flash("Erro interno ao tentar atualizar o token.", "danger")
    else:
        flash("Erro: Módulo do painel não carregado.", "danger")
    return redirect(url_for("painel"))

@app.route("/resetar_acesso") 
def resetar_acesso():
    """Limpa a sessão de acesso do usuário."""
    session.pop('acesso_concluido', None)
    session.pop('user_token', None)
    session.modified = True
    logging.info("Sessão de acesso resetada a pedido.")
    return "Sessão de acesso resetada. <a href='/'>Voltar ao início</a>"

# Bloco main 
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
    logging.info(f"Iniciando app Flask em host=0.0.0.0, port={port}, debug={debug_mode}")
    app.run(debug=debug_mode, host='0.0.0.0', port=port)

@app.route("/get_historico", methods=["POST"])
def get_historico():
    data = request.get_json()
    telefone = data.get("telefone")

    if not telefone:
        return jsonify({"status": "erro", "mensagem": "Telefone não enviado"}), 400

    historico = get_chat_history(telefone)
    return jsonify(historico)
