# painel/__init__.py (VERSÃO ATUALIZADA - PÓS Passo 2.1)

import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone # Import timezone from datetime
import secrets
import logging

# Importa pytz se disponível 
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

# (Função do Passo 1.1 - Mantida)
def criar_tabela_tokens():
    """Cria a tabela de tokens de acesso (nova estrutura com nome e telefone), se não existir."""
    if not DATABASE_URL:
        logging.error("DATABASE_URL não definida. Impossível criar tabela 'tokens'.")
        return
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    id SERIAL PRIMARY KEY,                  
                    nome TEXT NOT NULL,                     
                    telefone TEXT NOT NULL UNIQUE,          
                    token TEXT NOT NULL UNIQUE,             
                    criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
                    validade_em TIMESTAMP WITH TIME ZONE      
                );
            """)
            cur.execute(""" CREATE INDEX IF NOT EXISTS idx_tokens_token ON tokens (token); """)
            cur.execute(""" CREATE INDEX IF NOT EXISTS idx_tokens_telefone ON tokens (telefone); """) 
        conn.commit()
        logging.info("Tabela 'tokens' verificada/criada com sucesso (nova estrutura).")
    except psycopg2.Error as e:
        logging.exception(f"Erro de banco de dados ao criar/verificar tabela 'tokens': {e.pgcode} - {e.pgerror}")
        if conn: conn.rollback()
    except Exception as e:
        logging.exception("Erro inesperado ao criar/verificar tabela 'tokens'")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()

# (Função auxiliar - Mantida)
def gerar_token():
    """Gera um token seguro."""
    return secrets.token_urlsafe(16)

# (Função do Passo 1.2 - Mantida)
def inserir_token(nome: str, telefone: str, dias_validade: int) -> str | None:
    """
    Insere um novo token associado a um nome e telefone único.
    Retorna o token gerado em caso de sucesso.
    Retorna None em caso de erro OU se o telefone já existir no banco.
    """
    if not DATABASE_URL:
        logging.error("DATABASE_URL não definida. Impossível inserir token.")
        return None
    if not nome or not telefone:
         logging.warning("Tentativa de inserir token com nome ou telefone vazio.")
         return None

    conn = None
    token_novo = gerar_token()
    agora_utc = datetime.now(timezone.utc)
    validade_utc = agora_utc + timedelta(days=int(dias_validade)) 

    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tokens (nome, telefone, token, criado_em, validade_em)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (nome, telefone, token_novo, agora_utc, validade_utc)
            )
        conn.commit()
        logging.info(f"Token inserido com sucesso para: Nome='{nome}', Telefone='***{telefone[-4:]}', Token='{token_novo[:8]}...'")
        return token_novo

    except psycopg2.errors.UniqueViolation as e:
        logging.warning(f"Tentativa de inserir telefone duplicado: '***{telefone[-4:]}'. O usuário '{nome}' já pode ter um token.")
        if conn: conn.rollback()
        return None 

    except psycopg2.Error as e:
        logging.exception(f"Erro de banco de dados ao inserir token para Nome='{nome}', Telefone='***{telefone[-4:]}': {e.pgcode} - {e.pgerror}")
        if conn: conn.rollback()
        return None

    except Exception as e:
        logging.exception(f"Erro inesperado ao inserir token para Nome='{nome}', Telefone='***{telefone[-4:]}'")
        if conn: conn.rollback()
        return None

    finally:
        if conn: conn.close()

# (Função do Passo 1.4 - Mantida)
def listar_tokens() -> list[tuple[str, str, str, str | None, str | None]]:
    """
    Lista todos os tokens do banco, retornando nome, telefone, token e datas formatadas.
    Retorna uma lista de tuplas: [(nome, telefone, token, criado_em_str, validade_em_str), ...]
    """
    if not DATABASE_URL:
        logging.error("DB URL não definida. Impossível listar tokens.")
        return []
    conn = None
    tokens_raw = []
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT nome, telefone, token, criado_em, validade_em 
                FROM tokens 
                ORDER BY criado_em DESC
            """)
            tokens_raw = cur.fetchall()
            logging.info(f"Listados {len(tokens_raw)} tokens raw do banco.")
    except psycopg2.Error as e:
        logging.exception(f"Erro de banco de dados ao listar tokens: {e.pgcode} - {e.pgerror}"); return []
    except Exception as e:
         logging.exception("Erro inesperado ao listar tokens"); return []
    finally:
        if conn: conn.close()

    tokens_formatados = []
    fuso_brasil = None
    if PYTZ_IMPORTADO:
        try: fuso_brasil = pytz_timezone("America/Sao_Paulo")
        except Exception as tz_e: logging.warning(f"Erro timezone SP: {tz_e}. Usando UTC para formatação.")

    for nome, telefone, tok, cr_dt, vd_dt in tokens_raw: 
        if cr_dt and cr_dt.tzinfo is None: cr_dt = cr_dt.replace(tzinfo=timezone.utc)
        if vd_dt and vd_dt.tzinfo is None: vd_dt = vd_dt.replace(tzinfo=timezone.utc)
        cr_final_dt = cr_dt.astimezone(fuso_brasil) if fuso_brasil and cr_dt else cr_dt
        vd_final_dt = vd_dt.astimezone(fuso_brasil) if fuso_brasil and vd_dt else vd_dt
        cr_final_str = cr_final_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z') if cr_final_dt else None
        vd_final_str = vd_final_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z') if vd_final_dt else None
        tokens_formatados.append((nome, telefone, tok, cr_final_str, vd_final_str))
        
    logging.info(f"Retornando {len(tokens_formatados)} tokens formatados.")
    return tokens_formatados

# (Função original - Mantida)
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
        else: logging.warning(f"Token não encontrado para exclusão: {token[:8]}..."); return False
    except psycopg2.Error as e:
        logging.exception(f"Erro de BD ao excluir token {token[:8]}: {e.pgcode} - {e.pgerror}")
        if conn: conn.rollback()
        return False
    except Exception as e:
        logging.exception(f"Erro inesperado ao excluir token: {token[:8]}...")
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# 👇👇👇 NOVA FUNÇÃO ADICIONADA (Passo 2.1) 👇👇👇
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
def verificar_token_valido(token_a_verificar: str) -> bool:
    """
    Verifica se um token existe no banco de dados e se ainda está dentro do prazo de validade.
    Retorna True se o token existe e é válido, False caso contrário.
    """
    if not DATABASE_URL:
        logging.error("DATABASE_URL não definida. Impossível verificar token.")
        return False
    if not token_a_verificar:
        logging.warning("Tentativa de verificar token vazio.")
        return False

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT validade_em FROM tokens WHERE token = %s
                """,
                (token_a_verificar,)
            )
            resultado = cur.fetchone() 

        if resultado is None:
            logging.info(f"Token não encontrado no BD: {token_a_verificar[:8]}...")
            return False 

        validade_db = resultado[0] 
        if validade_db is None:
             logging.warning(f"Token {token_a_verificar[:8]}... encontrado, mas sem data de validade definida.")
             return False

        agora_utc = datetime.now(timezone.utc)

        if agora_utc < validade_db:
            logging.debug(f"Token válido encontrado: {token_a_verificar[:8]}...")
            return True 
        else:
            logging.info(f"Token encontrado, mas expirado: {token_a_verificar[:8]}... Validade: {validade_db}")
            return False 

    except psycopg2.Error as e:
        logging.exception(f"Erro de BD ao verificar token {token_a_verificar[:8]}...: {e.pgcode} - {e.pgerror}")
        return False 
    except Exception as e:
        logging.exception(f"Erro inesperado ao verificar token {token_a_verificar[:8]}...")
        return False 
    finally:
        if conn:
            conn.close()
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# 👆👆👆 NOVA FUNÇÃO ADICIONADA (Passo 2.1) 👆👆👆
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<


# --- Funções de Chat History (mantidas como antes) ---

def criar_tabela_chat_history():
    """Cria a tabela para armazenar o histórico de chat, se não existir."""
    # (Código original mantido)
    # ... (resto da função como antes) ...
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
        if conn: conn.rollback()
    finally:
        if conn: conn.close()


def add_chat_message(user_token: str, role: str, content: str) -> bool:
    """Adiciona uma mensagem (user ou assistant) ao histórico no banco."""
    # (Código original mantido)
    # ... (resto da função como antes) ...
    if not DATABASE_URL or not user_token or role not in ('user', 'assistant') or content is None: logging.warning(f"Tentativa msg chat inválida. Token:{user_token[:8] if user_token else 'N/A'} R:{role}"); return False
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO chat_messages (user_token, role, content) VALUES (%s, %s, %s)""", (user_token, role, content))
        conn.commit(); logging.info(f"Msg salva BD token {user_token[:8]} R:{role}"); return True
    except Exception as e:
        logging.exception(f"Erro salvar msg BD token {user_token[:8]}")
        if conn: conn.rollback()
        return False
    finally:
        if conn: conn.close()


def get_chat_history(user_token: str, limit: int = 20) -> list:
    """Busca as últimas 'limit' mensagens (pares user/assistant) para um token."""
    # (Código original mantido)
    # ... (resto da função como antes) ...
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