import subprocess

from alembic import config, script
from alembic.runtime import migration

from cms_backend import logger
from cms_backend.context import Context
from cms_backend.db import Session


def check_if_schema_is_up_to_date():
    with Session.begin() as session:
        logger.info("Checking database schema")
        cfg = config.Config(Context.base_dir / "alembic.ini")
        cfg.set_main_option("script_location", "cms_backend:migrations")
        directory = script.ScriptDirectory.from_config(cfg)
        context = migration.MigrationContext.configure(session.connection())
        current_heads = set(context.get_current_heads())
        directory_heads = set(directory.get_heads())
        logger.info(f"current heads: {current_heads}")
        logger.info(f"directory heads: {directory_heads}")
        if current_heads != directory_heads:
            raise ValueError(
                "Database schema is not up to date, please update schema first"
            )
        logger.info("Database is up to date")


def upgrade_db_schema():
    """Checks if Alembic schema has been applied to the DB"""
    logger.info(f"Upgrading database schema with config in {Context.base_dir}")
    subprocess.check_output(args=["alembic", "upgrade", "head"], cwd=Context.base_dir)
