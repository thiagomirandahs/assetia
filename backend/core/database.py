"""Conexao com o banco e sessao SQLAlchemy 2.0."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    """Base declarativa do SQLAlchemy 2.0."""


def _make_engine():
    s = get_settings()
    connect_args = {"check_same_thread": False} if s.database_url.startswith("sqlite") else {}
    return create_engine(s.database_url, connect_args=connect_args, pool_pre_ping=True)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Dependency injection do FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Cria as tabelas se nao existirem. Chame no startup da app."""
    # Importa modelos antes de criar (registra metadata)
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _migrar_colunas()


def _migrar_colunas():
    """Migracao leve: adiciona colunas novas a tabelas existentes (ADD COLUMN idempotente).

    create_all() so cria tabelas que faltam — nao altera tabelas ja existentes. Este passo
    cobre colunas adicionadas depois (ex: pentest: devices.risco_score, portas.cves).
    """
    from sqlalchemy import inspect, text

    novas = {
        "devices": [("risco_score", "INTEGER")],
        "portas": [("cves", "TEXT")],
    }
    insp = inspect(engine)
    tabelas = set(insp.get_table_names())
    with engine.begin() as conn:
        for tabela, colunas in novas.items():
            if tabela not in tabelas:
                continue
            existentes = {c["name"] for c in insp.get_columns(tabela)}
            for nome, tipo in colunas:
                if nome not in existentes:
                    conn.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {nome} {tipo}"))
