# app.py (Completo e com ajuste final para 'mensagem')

import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from dotenv import load_dotenv
# Importa funções do seu módulo 'painel'. Garanta que ele exista e funcione.
try:
    from painel import criar_tabela_tokens, inserir_token, listar_tokens, excluir_token
    PAINEL_IMPORTADO = True
except ImportError:
    print("AVISO: Módulo 'painel' não encontrado ou com erro na importação. Funções do painel/token não funcionarão.")
    PAINEL_IMPORTADO = False
    # Define funções placeholder para evitar erros graves se o painel não for essencial agora
    def criar_tabela_tokens(): pass
    def inserir_token(uid, dias): print(f"Placeholder: Inserir token para {uid}"); return {"token": f"fake_token_{uid}"} # Retorna algo
    def listar_tokens(): print("Placeholder: Listar tokens"); return []
    def excluir_token(tok): print(f"Placeholder: Excluir token {tok}")


from datetime import datetime
from pytz import timezone

load_dotenv()

app = Flask(__name__)
# Defina PAINEL_SENHA no .env ou use uma chave segura aqui
app.secret_key = os.getenv("PAINEL_SENHA", "fallback-seguro-mas-trocar-depois")

# Tenta criar tabela de tokens
try:
    criar_tabela_tokens()
except Exception as e:
    print(f"AVISO: Não foi possível criar/verificar tabela de tokens: {e}")

# --- Constante para o Prompt da IA ---
SYSTEM_PROMPT = """Você é a Dra. Ana, uma assistente médica virtual especializada em saúde feminina.
Seu tom deve ser profissional, empático e informativo.
Responda às perguntas do usuário sobre saúde da mulher de forma clara e cuidadosa.
Lembre sempre ao usuário que você é uma IA e não substitui uma consulta médica real.
Não forneça diagnósticos médicos definitivos. Incentive o usuário a procurar um profissional de saúde."""

# --- Rotas do Fluxo Principal e Instalação ---

@app.route("/")
def index():
    return redirect(url_for("instalar"))

@app.route("/instalar")
def instalar():
    if session.get('acesso_concluido'):
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
        dias_validade = 7
        try:
            token_info = inserir_token(user_id, dias_validade)
            if not token_info and PAINEL_IMPORTADO: # Só falha se painel deveria existir
                 raise Exception("Falha ao inserir token (função retornou None/False)")

            session['acesso_concluido'] = True
            session.pop('chat_history', None) # Limpa histórico ao (re)conceder acesso
            session.modified = True # Garante que a remoção seja salva
            return redirect(url_for('dra_ana_route')) # Redireciona para o chat
        except Exception as e:
            print(f"Erro ao inserir token para {user_id}: {e}")
            return render_template("formulario_acesso.html", sucesso=False, erro="Ocorreu um erro ao processar seu acesso. Tente novamente."), 500

    # --- Lógica GET ---
    if session.get('acesso_concluido'):
        return redirect(url_for('dra_ana_route')) # Vai para o chat se já tem acesso
    else:
        return render_template("formulario_acesso.html", sucesso=False) # Mostra formulário

# --- Novas Rotas para o Chat com IA ---

# Rota para servir a página HTML do chat
@app.route("/dra-ana")
def dra_ana_route():
    """Serve a página principal do chat."""
    if not session.get('acesso_concluido'):
        return redirect(url_for('instalar'))
    return render_template("chat.html")

# Rota (API) para processar as mensagens do chat
@app.route("/chat", methods=["POST"])
def chat_endpoint():
    """Recebe mensagens do usuário e retorna respostas da IA."""
    if not session.get('acesso_concluido'):
        return jsonify({"error": "Acesso não autorizado"}), 403

    try:
        data = request.get_json()
        # VVV AJUSTE FINAL AQUI VVV
        user_message = data.get("mensagem") # Espera a chave 'mensagem' do JS
        # ^^^ AJUSTE FINAL AQUI ^^^
        user_id_from_js = data.get("user_id") # Pega o user_id do JS (localStorage)

        if not user_message:
            return jsonify({"error": "Mensagem não pode ser vazia"}), 400

        # Gerencia histórico na sessão
        if 'chat_history' not in session:
            session['chat_history'] = []

        # Limita tamanho do histórico (ex: últimas 10 trocas = 20 mensagens)
        MAX_HISTORY_LEN = 20
        while len(session['chat_history']) >= MAX_HISTORY_LEN:
            session['chat_history'].pop(0) # Remove a mensagem mais antiga

        session['chat_history'].append({"role": "user", "content": user_message})
        session.modified = True # Garante que a adição seja salva

        # --- LÓGICA PARA CHAMAR OPENROUTER VIRÁ AQUI ---
        # ***** Placeholder - Simplesmente ecoa a mensagem por enquanto *****
        try:
            messages_to_send = [{"role": "system", "content": SYSTEM_PROMPT}] + session['chat_history']
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                 raise ValueError("Chave da API OpenRouter não configurada.")

            # response = requests.post(...) # Chamada real comentada por enquanto

            # **** REMOVER ESTE PLACEHOLDER QUANDO A API FOR IMPLEMENTADA ****
            ai_response = f"Backend recebeu: '{user_message}' (ID JS: {user_id_from_js}). Resposta real da IA virá aqui."
            print(f"API Key (início): {api_key[:5]}...") # Debug
            print(f"Histórico enviado (simplificado): {len(messages_to_send)} mensagens")
            print(f"Resposta (placeholder): {ai_response}")
            # **** FIM DO PLACEHOLDER ****

            # Adiciona resposta (placeholder) ao histórico
            session['chat_history'].append({"role": "assistant", "content": ai_response})
            session.modified = True

            # Retorna a resposta (placeholder)
            return jsonify({"response": ai_response})

        except requests.exceptions.RequestException as e:
            print(f"Erro de rede ou API OpenRouter: {e}")
            return jsonify({"error": "Não foi possível conectar ao serviço de IA."}), 503
        except ValueError as e:
             print(f"Erro de configuração: {e}")
             return jsonify({"error": str(e)}), 500
        except Exception as e:
            print(f"Erro inesperado ao processar chat: {e}")
            return jsonify({"error": "Ocorreu um erro interno ao gerar a resposta."}), 500
        # --- FIM DA LÓGICA (REAL) DA IA ---

    except Exception as e:
        print(f"Erro geral no endpoint /chat: {e}")
        return jsonify({"error": "Erro interno no servidor"}), 500

# --- Rotas do Painel de Admin (sem mudanças na lógica principal) ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        senha = request.form.get("senha")
        senha_painel = os.getenv("PAINEL_SENHA")
        if senha_painel and senha == senha_painel:
            session["autenticado"] = True
            return redirect(url_for("painel"))
        else:
            return "❌ Senha incorreta ou não configurada", 401
    # Renderiza um formulário simples se GET
    return '''
        <form method="POST">
            <label>Senha do Painel: <input type="password" name="senha" required></label>
            <button type="submit">Entrar</button>
        </form>
    '''

@app.route("/logout")
def logout():
    session.clear() # Limpa toda a sessão (admin E usuário)
    return redirect(url_for("login"))

@app.route("/painel", methods=["GET", "POST"])
def painel():
    if not session.get("autenticado"): return redirect(url_for("login"))

    token_gerado_info = None
    erro_painel = None
    if request.method == "POST" and "user_id" in request.form:
        user_id = request.form.get("user_id")
        try:
            dias_validade = int(request.form.get("dias_validade", 7))
            if PAINEL_IMPORTADO:
                token_gerado_info = inserir_token(user_id, dias_validade)
            else:
                 erro_painel = "Módulo 'painel' não importado, não é possível gerar token."
        except ValueError:
             erro_painel = "Número de dias de validade inválido."
        except Exception as e:
            print(f"Erro ao gerar token no painel: {e}")
            erro_painel = f"Erro ao gerar token: {e}"

    tokens = []
    try:
        if PAINEL_IMPORTADO:
            tokens = listar_tokens()
        else:
             erro_painel = erro_painel + " Módulo 'painel' não importado, não é possível listar tokens." if erro_painel else "Módulo 'painel' não importado, não é possível listar tokens."
    except Exception as e:
        print(f"Erro ao listar tokens: {e}")
        erro_painel = erro_painel + f" Erro ao listar tokens: {e}" if erro_painel else f"Erro ao listar tokens: {e}"


    now = datetime.now(timezone("America/Sao_Paulo"))
    # Passa erro_painel para o template para poder exibi-lo
    return render_template("painel.html", token_gerado=token_gerado_info, tokens=tokens, now=now, erro=erro_painel)


@app.route("/excluir_token", methods=["POST"])
def excluir_token_route():
    if not session.get("autenticado"): return redirect(url_for("login"))
    token = request.form.get("token")
    if token:
        try:
            if PAINEL_IMPORTADO:
                excluir_token(token)
            else:
                 print("AVISO: Módulo 'painel' não importado, exclusão não realizada.")
                 # Adicionar feedback para o admin seria ideal (usando flash ou passando variável)
        except Exception as e:
            print(f"Erro ao excluir token: {e}")
            # Adicionar feedback para o admin
    return redirect(url_for("painel"))

# Rota de teste para limpar sessão de acesso
@app.route("/resetar_acesso")
def resetar_acesso():
    session.pop('acesso_concluido', None)
    session.pop('chat_history', None)
    session.modified = True
    return "Sessão de acesso e histórico de chat resetados. <a href='/'>Voltar ao início</a>"

# Execução principal
if __name__ == "__main__":
    # Define a porta padrão 5000, mas permite override pela variável de ambiente PORT (usado pelo Render)
    port = int(os.environ.get('PORT', 5000))
    # host='0.0.0.0' permite acesso de fora do localhost (necessário para Render e testes em rede local)
    # debug=True deve ser False em produção (Gunicorn/Render cuidam disso)
    app.run(debug=True, host='0.0.0.0', port=port)




