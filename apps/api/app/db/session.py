from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.models import Agent, Organization, OrganizationMember, User, Workspace

settings = get_settings()


def _seed_sqlite_fallback(target_engine) -> None:
    with Session(target_engine) as session:
        u1 = session.get(User, 1)
        if u1 is None:
            org = Organization(id=1, name='Default Organization', slug='default-organization')
            user = User(
                id=1,
                email='user@example.com',
                password_hash=hash_password('devpassword123'),
                full_name='Default User',
                is_active=True,
            )
            workspace = Workspace(id=1, organization_id=1, owner_id=1, name='Default Workspace', slug='default-workspace')
            membership = OrganizationMember(organization_id=1, user_id=1, role='admin', status='active')
            session.add_all([org, user, workspace, membership])
            session.commit()
        elif u1.password_hash == 'hash':
            u1.password_hash = hash_password('devpassword123')
            session.commit()

        if session.get(Agent, 1) is None:
            a1 = Agent(id=1, workspace_id=1, name='Research Agent', slug='research-agent', description='Deep web research, synthesis, and fact verification.', provider='openai', model_name='gpt-4o-mini', status='active')
            a2 = Agent(id=2, workspace_id=1, name='Content Agent', slug='content-agent', description='Strategic content generation for blog, social, email, product and reports.', provider='openai', model_name='gpt-4o-mini', status='active')
            a3 = Agent(id=3, workspace_id=1, name='Data Analyst Agent', slug='data-analyst-agent', description='Data parsing, statistical profiling, and business intelligence.', provider='openai', model_name='gpt-4o-mini', status='active')
            session.add_all([a1, a2, a3])
            session.commit()


def _build_engine():
    global engine

    database_url = settings.database_url

    if settings.is_production:
        if 'postgres' not in database_url:
            raise RuntimeError('Production requires a PostgreSQL database connection string.')
        prod_engine = create_engine(database_url, pool_pre_ping=True)
        try:
            with prod_engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            return prod_engine
        except Exception as exc:
            raise RuntimeError(
                f'Production database startup check failed: could not connect to PostgreSQL ({exc}).'
            ) from exc

    # Development / Testing environment
    connect_args = {}
    if 'postgres' in database_url:
        connect_args['connect_timeout'] = 2

    dev_engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
    try:
        with dev_engine.connect() as connection:
            connection.execute(text('SELECT 1'))
        return dev_engine
    except (OperationalError, Exception) as exc:
        if not settings.allow_sqlite_fallback:
            raise RuntimeError(
                f'Database connection to {database_url} failed and SQLite fallback is disabled.'
            ) from exc

        sqlite_url = 'sqlite:///./helios_iq.db'
        fallback_engine = create_engine(sqlite_url, connect_args={'check_same_thread': False})
        Base.metadata.create_all(bind=fallback_engine)
        _seed_sqlite_fallback(fallback_engine)
        return fallback_engine



engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
