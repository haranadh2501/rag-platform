"""Quick connectivity check and table listing for Neon DB."""
import psycopg2, sys

url = (
    "postgresql://neondb_owner:npg_pZfyDjkngM74"
    "@ep-plain-shadow-aowguhj1-pooler.c-2.ap-southeast-1.aws.neon.tech"
    "/neondb?sslmode=require"
)

try:
    conn = psycopg2.connect(url)
    cur = conn.cursor()

    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' ORDER BY table_name"
    )
    tables = [r[0] for r in cur.fetchall()]
    print("Tables:", tables)

    if "conversations" in tables:
        cur.execute("SELECT COUNT(*) FROM conversations WHERE user_id IS NULL")
        nulls = cur.fetchone()[0]
        print(f"conversations with NULL user_id: {nulls}")

    if "alembic_version" in tables:
        cur.execute("SELECT version_num FROM alembic_version")
        print("Alembic revision:", cur.fetchone())
    else:
        print("Alembic revision: (no alembic_version table yet)")

    conn.close()
    print("Connection OK")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
