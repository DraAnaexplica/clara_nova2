import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta
import secrets
from pytz import timezone

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def criar_tabela_tokens():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                token TEXT NOT NULL UNIQUE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                validade_em TIMESTAMP
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Tabela 'tokens' criada/verificada com sucesso.")
    except Exception as e:
        print("❌ Erro ao criar tabela:", str(e))


def gerar_token():
    return secrets.token_urlsafe(16)


def inserir_token(user_id, dias_validade):
    token = gerar_token()
    fuso_brasil = timezone("America/Sao_Paulo")
    agora = datetime.now(fuso_brasil)
    validade = agora + timedelta(days=int(dias_validade))

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tokens (user_id, token, criado_em, validade_em)
            VALUES (%s, %s, %s, %s)
        """, (user_id, token, agora, validade))
        conn.commit()
        cur.close()
        conn.close()
        return token
    except Exception as e:
        print("Erro ao inserir token:", str(e))
        return None


def listar_tokens():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT user_id, token, criado_em, validade_em FROM tokens ORDER BY criado_em DESC")
        tokens_raw = cur.fetchall()
        cur.close()
        conn.close()

        fuso_brasil = timezone("America/Sao_Paulo")
        tokens = []
        for user_id, token, criado_em, validade_em in tokens_raw:
            tokens.append((
                user_id,
                token,
                criado_em.astimezone(fuso_brasil),
                validade_em.astimezone(fuso_brasil)
            ))
        return tokens
    except Exception as e:
        print("Erro ao listar tokens:", str(e))
        return []


def excluir_token(token):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("DELETE FROM tokens WHERE token = %s", (token,))
        conn.commit()
        cur.close()
        conn.close()
        print(f"🗑️ Token excluído: {token}")
    except Exception as e:
        print("Erro ao excluir token:", str(e))



