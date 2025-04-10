# painel/__init__.py (Passo 1.1 e 1.2 - Tabela e Inserir Token Modificados)

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

# --- Funções de Tokens (Revisadas) ---

# VVVVV Função criar_tabela_tokens MODIFICADA (Passo 1.1) VVVVV
def criar_tabela_tokens():
    """Cria a tabela de tokens com colunas separadas para nome e telefone (UNIQUE)."""
    if not DATABASE_URL: logging.error("DB URL não definida."); return
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
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
            cur.execute(""" CREATE INDEX IF NOT EXISTS idx_tokens_token ON tokens (token); """)
            cur.execute(""" CREATE INDEX IF NOT EXISTS idx_tokens_telefone ON tokens (telefone); """)
        conn.commit(); logging.info("Tabela 'tokens' (com telefone UNIQUE) OK.")
    except Exception as e: logging.exception("Erro criar/verificar tabela 'tokens'"); if conn: conn.rollback()
    finally:
        if conn: conn.close()
# ^^^^^ Fim da função criar_tabela_tokens modificada ^^^^^


def gerar_token(): return secrets.token_urlsafe(16)


# VVVVV Função inserir_token MODIFICADA (Passo 1.2) VVVVV
def inserir_token(nome: str, telefone: str, dias_validade: int) -> str | bool | None:
    """
    Insere um novo token, associado a um nome e telefone.
    Limpa o telefone para guardar só dígitos. Impede telefones duplicados.
    Retorna: str (token) em sucesso, False se telefone duplicado, None em outros erros.
    """
    if not DATABASE_URL: logging.error("DB URL não definida."); return None

    # Limpa o telefone para guardar apenas dígitos
    if telefone:
        telefone_limpo = re.sub(r'\D', '', telefone)
        if len(telefone_limpo) < 10: # Validação mínima (ex: DDD + 8 digitos) - AJUSTE SE NECESSÁRIO
             logging.warning(f"Número de telefone parece inválido (curto): {telefone} -> {telefone_limpo}")
             return None # Retorna None para erro de formato/curto demais
    else:
        logging.warning("Tentativa de inserir token sem número de telefone.")
        return None

    conn = None; token = gerar_token()
    agora_utc = datetime.now(timezone.utc)
    validade_utc = agora_utc + timedelta(days=int(dias_validade))

    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            # Usa as novas colunas 'nome' e 'telefone' (limpo)
            cur.execute("""
                INSERT INTO tokens (nome, telefone, token, criado_em, validade_em)
                VALUES (%s, %s, %s, %s, %s)
            """, (nome, telefone_limpo, token, agora_utc, validade_utc))
        conn.commit(); logging.info(f"Token inserido para: {nome} / {telefone_limpo}")
        return token # Retorna o token em caso de SUCESSO

    except psycopg2.errors.UniqueViolation:
        logging.warning(f"Tentativa de inserir telefone duplicado: {telefone_limpo}")
        if conn: conn.rollback()
        return False # Retorna False para indicar DUPLICIDADE

    except Exception as e:
        logging.exception(f"Erro genérico ao inserir token para: {nome} / {telefone_limpo}")
        if conn: conn.rollback()
        return None # Retorna None para indicar OUTRO ERRO

    finally:
        if conn: conn.close()
# ^^^^^ Fim da função inserir_token modificada ^^^^^


# !!! ATENÇÃO: Esta função listar_tokens ainda precisa ser modificada (próximo passo) !!!
def listar_tokens() -> list:
    """Lista todos os tokens do banco."""
    if not DATABASE_URL: logging.error("DB URL não definida."); return []
    conn = None; tokens_raw = []
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
             # AINDA USA user_id - PRECISA MUDAR PARA nome, telefone
            cur.execute("SELECT user_id, token, criado_em, validade_em FROM tokens ORDER BY criado_em DESC"); tokens_raw = cur.fetchall()
    except Exception as e: logging.exception("Erro ao listar tokens do BD"); return []
    finally:
        if conn: conn.close()

    tokens_formatados = []; fuso_brasil = None
    if PYTZ_IMPORTADO:
        try: fuso_brasil = pytz_timezone("America/Sao_Paulo")
        except Exception as tz_e: logging.warning(f"Erro timezone SP: {tz_e}. Usando UTC.")

    # PRECISA MUDAR O LOOP PARA USAR nome, telefone
    for uid, tok, cr, vd in tokens_raw:
        if cr and cr.tzinfo is None: cr = cr.replace(tzinfo=timezone.utc)
        if vd and vd.tzinfo is None: vd = vd.replace(tzinfo=timezone.utc)
        cr_final_dt = cr.astimezone(fuso_brasil) if fuso_brasil and cr else cr
        vd_final_dt = vd.astimezone(fuso_brasil) if fuso_brasil and vd else vd
        cr_final_str = cr_final_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z') if cr_final_dt else None
        vd_final_str = vd_final_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z') if vd_final_dt else None
        tokens_formatados.append((uid, tok, cr_final_str, vd_final_str)) # PRECISA MUDAR uid para nome, telefone

    return tokens_formatados

# Função excluir_token continua igual (exclui por token)
def excluir_token(token: str) -> bool:
    # ... (código como estava antes, já corrigido) ...
    if not DATABASE_URL or not token: logging.error("DB URL/token ausente."); return False
    conn = None; rows_deleted = 0
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur: cur.execute("DELETE FROM tokens WHERE token = %s", (token,)); rows_deleted = cur.rowcount
        conn.commit()
        if rows_deleted > 0: logging.info(f"Token excluído: {token[:8]}..."); return True
        else: logging.warning(f"Token não encontrado: {token[:8]}..."); return False
    except Exception as e: logging.exception(f"Erro ao excluir token: {token[:8]}..."); if conn: conn.rollback(); return False
    finally:
        if conn: conn.close()

# --- Funções de Chat History (sem mudanças agora) ---
def criar_tabela_chat_history():
    # ... (código como antes) ...
    pass # Cole aqui a função completa
def add_chat_message(user_token: str, role: str, content: str) -> bool:
    # ... (código como antes) ...
    pass # Cole aqui a função completa
def get_chat_history(user_token: str, limit: int = 20) -> list:
    # ... (código como antes) ...
    pass # Cole aqui a função completa
