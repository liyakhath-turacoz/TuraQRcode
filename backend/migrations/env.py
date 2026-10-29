from alembic import context
from sqlalchemy import text
from app.db import Base, engine
from app import models

config=context.config


def include_name(name,type_,parent_names):
    if type_=='schema': return name=='tura'
    return True


if context.is_offline_mode():
    raise RuntimeError('Online migration required to ensure the private schema exists.')
else:
    with engine().connect() as connection:
        connection.execute(text('CREATE SCHEMA IF NOT EXISTS tura'))
        connection.commit()
        context.configure(connection=connection,target_metadata=Base.metadata,include_schemas=True,include_name=include_name,version_table_schema='tura',compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
