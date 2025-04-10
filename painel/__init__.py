# painel/__init__.py (Passo 1.1 Aplicado na sua versão)

import os
import psycopg2
from dotenv import load_dotenv
# CORREÇÃO: Importar timezone de datetime
from datetime import datetime, timedelta, timezone
import secrets
import logging

# Importa pytz se disponível (mantendo como estava na sua versão)
try:
    from pytz import timezone as pytz_timezone
    PYTZ_IMPORTADO = True
except ImportError:
    PYTZ_IMPORTADO = False
    logging.warning("Biblioteca 'pytz' não encontrada no painel. Usando UTC/placeholder.")
    class pytz_timezone:
        def __init__(self, tz_name):
            pass

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carrega variáveis de ambiente
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# --- Funções de Tokens ---

# VVVVV FUNÇÃO MODIFICADA ABAIXO (Passo 1.1) VVVVV
def criar_tabela_tokens():
    """Cria a tabela de tokens com colunas separadas para nome e telefone (UNIQUE)."""
    if not DATABASE_URL:
        logging.error("DATABASE_URL não definida. Não é possível criar tabela de tokens.")
        return
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            # ***** ESTRUTURA ALTERADA *****
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    id SERIAL PRIMARY KEY,
                    nome TEXT,                      -- Coluna separada para o nome
                    telefone TEXT NOT NULL UNIQUE,  -- Telefone separado e ÚNICO
                    token TEXT NOT NULL UNIQUE,
                    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    validade_em TIMESTAMP WITH TIME ZONE
                );
            """)
            # Mantém índice no token, adiciona índice no telefone
            cur.execute(""" CREATE INDEX IF NOT EXISTS idx_tokens_token ON tokens (token); """)
            cur.execute(""" CREATE INDEX IF NOT EXISTS idx_tokens_telefone ON tokens (telefone); """)
            # ***** FIM DA ALTERAÇÃO *****
        conn.commit()
        logging.info("Tabela 'tokens' (com telefone UNIQUE) OK.") # Log atualizado
    except Exception as e:
        # Bloco except formatado corretamente
        logging.exception("Erro criar/verificar tabela 'tokens'")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
# ^^^^^ FIM DA FUNÇÃO MODIFICADA ^^^^^


def gerar_token(): return secrets.token_urlsafe(16)

# Função inserir_token (versão original sua, ainda com user_id)
# Vamos modificá-la no próximo passo
def inserir_token(user_id: str, dias_validade: int) -> str | None:
    """Insere um novo token no banco e retorna o token ou None."""
    if not DATABASE_URL: logging.error("DB URL não definida."); return None
    conn = None; token = gerar_token()
    agora_utc = datetime.now(timezone.utc) # Usa timezone importado de datetime
    validade_utc = agora_utc + timedelta(days=int(dias_validade))
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            # AINDA USA user_id - PRECISA MUDAR PARA nome, telefone no próximo passo
            cur.execute(""" INSERT INTO tokens (user_id, token, criado_em, validade_em) VALUES (%s, %s, %s, %s) """, (user_id, token, agora_utc, validade_utc))
        conn.commit(); logging.info(f"Token inserido para: {user_id}")
        return token
    except Exception as e:
        logging.exception(f"Erro inserir token user_id: {user_id}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn: conn.close()

# Função listar_tokens (versão original sua, ainda com user_id)
# Vamos modificá-la depois
def listar_tokens() -> list:
    """Lista todos os tokens do banco."""
    if not DATABASE_URL: logging.error("DB URL não definida."); return []
    conn = None; tokens_raw = []
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            # AINDA USA user_id - PRECISA MUDAR PARA nome, telefone depois
            cur.execute("SELECT user_id, token, criado_em, validade_em FROM tokens ORDER BY criado_em DESC"); tokens_raw = cur.fetchall()
    except Exception as e: logging.exception("Erro ao listar tokens do BD"); return []
    finally:
        if conn: conn.close()

    tokens_formatados = []; fuso_brasil = None
    if PYTZ_IMPORTADO:
        try: fuso_brasil = pytz_timezone("America/Sao_Paulo")
        except Exception as tz_e: logging.warning(f"Erro timezone SP: {tz_e}. Usando UTC.")

    # PRECISA MUDAR O LOOP PARA USAR nome, telefone depois
    for uid, tok, cr, vd in tokens_raw:
        if cr and cr.tzinfo is None: cr = cr.replace(tzinfo=timezone.utc) # Usa datetime.timezone.utc
        if vd and vd.tzinfo is None: vd = vd.replace(tzinfo=timezone.utc) # Usa datetime.timezone.utc
        cr_final_dt = cr.astimezone(fuso_brasil) if fuso_brasil and cr else cr
        vd_final_dt = vd.astimezone(fuso_brasil) if fuso_brasil and vd else vd
        cr_final_str = cr_final_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z') if cr_final_dt else None
        vd_final_str = vd_final_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z') if vd_final_dt else None
        # PRECISA MUDAR uid para nome, telefone depois
        tokens_formatados.append((uid, tok, cr_final_str, vd_final_str))
    return tokens_formatados

# Função excluir_token (versão original sua, já corrigida)
def excluir_token(token: str) -> bool:
    """Exclui um token específico do banco."""
    if not DATABASE_URL or not token: logging.error("DB URL/token ausente."); return False
    conn = None; rows_deleted = 0
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tokens WHERE token = %s", (token,))
            rows_deleted = cur.rowcount
        conn.commit()
        if rows_deleted > 0: logging.info(f"Token excluído: {token[:8]}..."); return True
        else: logging.warning(f"Token não encontrado: {token[:8]}..."); return False
    except Exception as e:
        logging.exception(f"Erro ao excluir token: {token[:8]}...")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn: conn.close()

# --- Funções de Chat History (como estavam na sua versão) ---
# Cole aqui suas funções: criar_tabela_chat_history, add_chat_message, get_chat_history

def criar_tabela_chat_history():
    """Cria a tabela para armazenar o histórico de chat, se não existir."""
    # ... (cole seu código completo aqui) ...
    pass

def add_chat_message(user_token: str, role: str, content: str) -> bool:
    """Adiciona uma mensagem (user ou assistant) ao histórico no banco."""
    # ... (cole seu código completo aqui) ...
    pass

def get_chat_history(user_token: str, limit: int = 20) -> list:
    """Busca as últimas 'limit' mensagens (pares user/assistant) para um token."""
    # ... (cole seu código completo aqui) ...
    pass
