# painel/__init__.py (VERSÃO REALMENTE FINAL CORRIGIDA)

import os
import psycopg2
import psycopg2.errors # Importa para pegar erro de duplicidade
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone # Import timezone from datetime
import secrets
import logging
import re # Importa para limpeza do telefone

# Importa pytz se disponível
try:
    from pytz import timezone as pytz_timezone
    PYTZ_IMPORTADO = True
except ImportError:
    PYTZ_IMPORTADO = False
    logging.warning("Biblioteca 'pytz' não encontrada no painel. Usando UTC/placeholder.")
    class pytz_timezone: # Placeholder com indentação correta
        def __init__(self, tz_name):
            pass

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carrega variáveis de ambiente
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# --- Funções de Tokens (Revisadas com 'with' e formatação de 'except') ---

def criar_tabela_tokens():
    """Cria a tabela de tokens com colunas separadas para nome e telefone (UNIQUE)."""
    if not DATABASE_URL: logging.error("DB URL não definida."); return
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    id SERIAL PRIMARY KEY, nome TEXT, telefone TEXT NOT NULL UNIQUE, token TEXT NOT NULL UNIQUE,
                    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, validade_em TIMESTAMP WITH TIME ZONE );
            """)
            cur.execute(""" CREATE INDEX IF NOT EXISTS idx_tokens_token ON tokens (token); """)
            cur.execute(""" CREATE INDEX IF NOT EXISTS idx_tokens_telefone ON tokens (telefone); """)
        conn.commit(); logging.info("Tabela 'tokens' (com telefone UNIQUE) OK.")
    except Exception as e:
        # Except formatado corretamente
        logging.exception("Erro criar/verificar tabela 'tokens'")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()

def gerar_token(): return secrets.token_urlsafe(16)

def inserir_token(nome: str, telefone: str, dias_validade: int) -> str | bool | None:
    """Insere token com nome/telefone. Retorna token, False (duplicado), ou None (erro)."""
    if not DATABASE_URL: logging.error("DB URL não definida."); return None
    if telefone: telefone_limpo = re.sub(r'\D', '', telefone); assert len(telefone_limpo) >= 10, "Tel muito curto"
    else: logging.warning("Inserir token sem telefone."); return None
    conn = None; token = gerar_token()
    agora_utc = datetime.now(timezone.utc); validade_utc = agora_utc + timedelta(days=int(dias_validade))
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute(""" INSERT INTO tokens (nome, telefone, token, criado_em, validade_em) VALUES (%s, %s, %s, %s, %s) """, (nome, telefone_limpo, token, agora_utc, validade_utc))
        conn.commit(); logging.info(f"Token inserido: {nome}/{telefone_limpo}"); return token
    except psycopg2.errors.UniqueViolation:
        # Except formatado corretamente
        logging.warning(f"Tentativa de inserir telefone duplicado: {telefone_limpo}")
        if conn: conn.rollback()
        return False # Retorna False para duplicidade
    except Exception as e:
        # Except formatado corretamente
        logging.exception(f"Erro genérico inserir token: {nome}/{telefone_limpo}")
        if conn: conn.rollback()
        return None # Retorna None para outros erros
    finally:
        if conn: conn.close()

def listar_tokens() -> list:
    """Lista todos os tokens (AINDA PRECISA DE AJUSTE PARA NOME/TELEFONE)."""
    # !!! ESTA FUNÇÃO PRECISA SER AJUSTADA NO PRÓXIMO PASSO !!!
    if not DATABASE_URL: logging.error("DB URL não definida."); return []
    conn = None; tokens_raw = []
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            # PRECISA MUDAR user_id para nome, telefone AQUI
            cur.execute("SELECT user_id, token, criado_em, validade_em FROM tokens ORDER BY criado_em DESC"); tokens_raw = cur.fetchall()
    except Exception as e: logging.exception("Erro ao listar tokens do BD"); return []
    finally:
        if conn: conn.close()

    tokens_formatados = []; fuso_brasil = None
    if PYTZ_IMPORTADO:
        try: fuso_brasil = pytz_timezone("America/Sao_Paulo")
        except Exception as tz_e: logging.warning(f"Erro timezone SP: {tz_e}. Usando UTC.")
    # PRECISA MUDAR O LOOP PARA RECEBER nome, telefone AQUI
    for uid, tok, cr, vd in tokens_raw:
        if cr and cr.tzinfo is None: cr = cr.replace(tzinfo=timezone.utc)
        if vd and vd.tzinfo is None: vd = vd.replace(tzinfo=timezone.utc)
        cr_final_dt = cr.astimezone(fuso_brasil) if fuso_brasil and cr else cr
        vd_final_dt = vd.astimezone(fuso_brasil) if fuso_brasil and vd else vd
        cr_final_str = cr_final_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z') if cr_final_dt else None
        vd_final_str = vd_final_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z') if vd_final_dt else None
        # PRECISA MUDAR uid para nome, telefone AQUI
        tokens_formatados.append((uid, tok, cr_final_str, vd_final_str))
    return tokens_formatados

def excluir_token(token: str) -> bool:
    """Exclui um token específico do banco."""
    if not DATABASE_URL or not token: logging.error("DB URL/token ausente."); return False
    conn = None; rows_deleted = 0
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur: cur.execute("DELETE FROM tokens WHERE token = %s", (token,)); rows_deleted = cur.rowcount
        conn.commit()
        if rows_deleted > 0: logging.info(f"Token excluído: {token[:8]}..."); return True
        else: logging.warning(f"Token não encontrado: {token[:8]}..."); return False
    except Exception as e:
        # Except formatado corretamente
        logging.exception(f"Erro ao excluir token: {token[:8]}...")
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()

# --- Funções de Chat History (Revisadas com 'with' e formatação de 'except') ---
def criar_tabela_chat_history():
    if not DATABASE_URL: logging.error("DB URL não definida."); return
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS chat_messages (...);""") # Use seu SQL completo aqui
            cur.execute("""CREATE INDEX IF NOT EXISTS idx_chat_msgs_user_token_ts ...;""") # Use seu SQL completo aqui
        conn.commit(); logging.info("Tabela 'chat_messages' OK.")
    except Exception as e:
        # Except formatado corretamente
        logging.exception("Erro criar tabela 'chat_messages'")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()

def add_chat_message(user_token: str, role: str, content: str) -> bool:
    if not DATABASE_URL or not user_token or role not in ('user', 'assistant') or content is None: logging.warning(...); return False
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur: cur.execute("""INSERT INTO chat_messages (user_token, role, content) VALUES (%s, %s, %s)""", (user_token, role, content))
        conn.commit(); logging.info(f"Msg salva BD token {user_token[:8]} R:{role}"); return True
    except Exception as e:
        # Except formatado corretamente
        logging.exception(f"Erro salvar msg BD token {user_token[:8]}")
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()

def get_chat_history(user_token: str, limit: int = 20) -> list:
    if not DATABASE_URL or not user_token: return []
    conn = None; history = []
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur: cur.execute("""SELECT role, content FROM (...) AS recent_messages ORDER BY timestamp ASC;""", (user_token, limit)) # Use sua query completa
            results = cur.fetchall()
        history = [{"role": row[0], "content": row[1]} for row in results]
        logging.info(f"Histórico lido BD token {user_token[:8]}: {len(history)} msgs")
    except Exception as e:
        # Except formatado corretamente
        logging.exception(f"Erro buscar hist BD token {user_token[:8]}")
    finally:
        if conn: conn.close()
    return history