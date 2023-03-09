import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from backend.models import Language, database

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# creating tables in an in-memory SQLITE so alembic knows about schema
Language.Meta.table.create(create_engine("sqlite://"))
target_metadata = Language.Meta.metadata
render_as_batch = True
database_url = (
    database.url.replace(dialect="mysql+pymysql")
    if "mysql" in database.url.dialect
    else database.url
)


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=re.sub(r"(\?.+)$", "", str(database_url)),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=render_as_batch,
        # if you use UUID field set also this param
        # the prefix has to match sqlalchemy import name in alembic
        # that can be set by sqlalchemy_module_prefix option (default 'sa.')
        user_module_prefix="sa.",
        # allows autogenerate to detect type changes
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    engine = create_engine(re.sub(r"(\?.+)$", "", str(database_url)))
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=render_as_batch,
            # if you use UUID field set also this param
            # the prefix has to match sqlalchemy import name in alembic
            # that can be set by sqlalchemy_module_prefix option (default 'sa.')
            user_module_prefix="sa.",
            # allows autogenerate to detect type changes
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
