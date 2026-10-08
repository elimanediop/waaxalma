from alembic import context
from sqlalchemy import create_engine, pool
import os
config=context.config
url=os.environ.get('DATABASE_URL')
if not url: raise RuntimeError('DATABASE_URL is required for Alembic')
url=url.replace('postgresql://','postgresql+psycopg://',1)
if context.is_offline_mode():
    context.configure(url=url, literal_binds=True)
    with context.begin_transaction(): context.run_migrations()
else:
    engine=create_engine(url,poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction(): context.run_migrations()
    engine.dispose()
