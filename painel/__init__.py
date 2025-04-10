# Em painel/__init__.py (Nova Versão - Passo 1.1)

import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone # Import timezone from datetime
import secrets
import logging

# Importa pytz se disponível (mantido como estava)
try:
    from pytz import timezone as pytz_timezone
    PYTZ_IMPORTADO = True
except ImportError:
    PYTZ_IMPORTADO = False
    logging.warning("Biblioteca 'pytz' não encontrada no painel. Usando UTC/placeholder.")
    class pytz_timezone: 
        def __init__(self, tz_name):
            pass

# Configuração básica de logging (mantido como estava)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carrega variáveis de ambiente (mantido como estava)
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# --- Funções de Tokens (Revisadas) ---

# 👇👇👇 FUNÇÃO MODIFICADA ABAIXO 👇👇👇
def criar_tabela_tokens():
    """Cria a tabela de tokens de acesso (nova estrutura com nome e telefone), se não existir."""
    if not DATABASE_URL: 
        logging.error("DATABASE_URL não definida. Impossível criar tabela 'tokens'.")
        return
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            # --- ALTERAÇÃO PRINCIPAL AQUI ---
            # Substituímos 'user_id TEXT NOT NULL' por 'nome TEXT NOT NULL' e 'telefone TEXT NOT NULL UNIQUE'
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    id SERIAL PRIMARY KEY,                   -- Mantém ID numérico autoincremental
                    nome TEXT NOT NULL,                      -- Coluna separada para nome
                    telefone TEXT NOT NULL UNIQUE,           -- Coluna separada para telefone, DEVE SER ÚNICO
                    token TEXT NOT NULL UNIQUE,              -- Token de acesso individual, também único
                    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- Data/hora criação com fuso
                    validade_em TIMESTAMP WITH TIME ZONE       -- Data/hora validade com fuso
                );
            """)
            # --- FIM DA ALTERAÇÃO ---
            
            # Cria índices para otimizar buscas (mantém o de token, adiciona o de telefone)
            cur.execute(""" CREATE INDEX IF NOT EXISTS idx_tokens_token ON tokens (token); """)
            cur.execute(""" CREATE INDEX IF NOT EXISTS idx_tokens_telefone ON tokens (telefone); """) # <-- Novo índice adicionado para telefone
            
        conn.commit()
        logging.info("Tabela 'tokens' verificada/criada com sucesso (nova estrutura).")
    except psycopg2.Error as e: # Captura erro específico do psycopg2
        logging.exception(f"Erro de banco de dados ao criar/verificar tabela 'tokens': {e.pgcode} - {e.pgerror}")
        if conn:
            conn.rollback() # Desfaz transação em caso de erro de BD
    except Exception as e: # Captura outros erros genéricos
        logging.exception("Erro inesperado ao criar/verificar tabela 'tokens'")
        if conn:
            conn.rollback() # Garante rollback em outros erros também
    finally:
        if conn: 
            conn.close()
# 👆👆👆 FUNÇÃO MODIFICADA ACIMA 👆👆👆

# --- O RESTANTE DAS FUNÇÕES (gerar_token, inserir_token, listar_tokens, etc.) ---
# --- CONTINUAM AQUI EXATAMENTE COMO VOCÊ ENVIOU, POR ENQUANTO ---
# --- VAMOS MODIFICÁ-LAS NOS PRÓXIMOS PASSOS ---

def gerar_token(): return secrets.token_urlsafe(16)

def inserir_token(user_id: str, dias_validade: int) -> str | None:
    """Insere um novo token no banco e retorna o token ou None."""
    # ... (código original SEM MODIFICAÇÃO AINDA) ...
    if not DATABASE_URL: logging.error("DB URL não definida."); return None
    conn = None; token = gerar_token()
    agora_utc = datetime.now(timezone.utc)
    validade_utc = agora_utc + timedelta(days=int(dias_validade))
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
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


def listar_tokens() -> list:
    """Lista todos os tokens do banco."""
     # ... (código original SEM MODIFICAÇÃO AINDA) ...
    if not DATABASE_URL: logging.error("DB URL não definida."); return []
    conn = None; tokens_raw = []
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur: cur.execute("SELECT user_id, token, criado_em, validade_em FROM tokens ORDER BY criado_em DESC"); tokens_raw = cur.fetchall()
    except Exception as e: logging.exception("Erro ao listar tokens do BD"); return []
    finally:
        if conn: conn.close()

    tokens_formatados = []; fuso_brasil = None
    if PYTZ_IMPORTADO:
        try: fuso_brasil = pytz_timezone("America/Sao_Paulo")
        except Exception as tz_e: logging.warning(f"Erro timezone SP: {tz_e}. Usando UTC.")
    for uid, tok, cr, vd in tokens_raw:
        if cr and cr.tzinfo is None: cr = cr.replace(tzinfo=timezone.utc)
        if vd and vd.tzinfo is None: vd = vd.replace(tzinfo=timezone.utc)
        cr_final_dt = cr.astimezone(fuso_brasil) if fuso_brasil and cr else cr
        vd_final_dt = vd.astimezone(fuso_brasil) if fuso_brasil and vd else vd
        cr_final_str = cr_final_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z') if cr_final_dt else None
        vd_final_str = vd_final_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z') if vd_final_dt else None
        tokens_formatados.append((uid, tok, cr_final_str, vd_final_str))
    return tokens_formatados


def excluir_token(token: str) -> bool:
    """Exclui um token específico do banco."""
    # ... (código original SEM MODIFICAÇÃO AINDA) ...
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

# --- Funções de Chat History (mantidas como estavam) ---
# ... (código original SEM MODIFICAÇÃO) ...
def criar_tabela_chat_history():
    """Cria a tabela para armazenar o histórico de chat, se não existir."""
    if not DATABASE_URL: logging.error("DB URL não definida."); return
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id SERIAL PRIMARY KEY, user_token TEXT NOT NULL, role TEXT NOT NULL CHECK (role IN ('user', 'assistant')), content TEXT NOT NULL, timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_msgs_user_token_ts
                ON chat_messages (user_token, timestamp DESC);
            """)
        conn.commit(); logging.info("Tabela 'chat_messages' OK.")
    except Exception as e:
        logging.exception("Erro criar tabela 'chat_messages'")
        if conn:
            conn.rollback()
    finally:
        if conn: conn.close()

def add_chat_message(user_token: str, role: str, content: str) -> bool:
    """Adiciona uma mensagem (user ou assistant) ao histórico no banco."""
    if not DATABASE_URL or not user_token or role not in ('user', 'assistant') or content is None: logging.warning(f"Tentativa msg chat inválida. Token:{user_token[:8] if user_token else 'N/A'} R:{role}"); return False
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO chat_messages (user_token, role, content) VALUES (%s, %s, %s)""", (user_token, role, content))
        conn.commit(); logging.info(f"Msg salva BD token {user_token[:8]} R:{role}"); return True
    except Exception as e:
        logging.exception(f"Erro salvar msg BD token {user_token[:8]}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn: conn.close()

def get_chat_history(user_token: str, limit: int = 20) -> list:
    """Busca as últimas 'limit' mensagens (pares user/assistant) para um token."""
    if not DATABASE_URL or not user_token: return []
    conn = None; history = []
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT role, content FROM (
                    SELECT role, content, timestamp FROM chat_messages WHERE user_token = %s ORDER BY timestamp DESC LIMIT %s
                ) AS recent_messages ORDER BY timestamp ASC;
            """, (user_token, limit))
            results = cur.fetchall()
        history = [{"role": row[0], "content": row[1]} for row in results]
        logging.info(f"Histórico lido BD token {user_token[:8]}: {len(history)} msgs")
    except Exception as e:
        logging.exception(f"Erro buscar hist BD token {user_token[:8]}")
    finally:
        if conn: conn.close()
    return history