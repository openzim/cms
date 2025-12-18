"""Fixtures for mill processors tests."""

import os
from uuid import uuid4

# Set up environment variables for MillContext before any imports
os.environ.setdefault("JAIL_WAREHOUSE_ID", str(uuid4()))
os.environ.setdefault("STAGING_WAREHOUSE_ID", str(uuid4()))
os.environ.setdefault("JAIL_BASE_PATH", "/jail")
os.environ.setdefault("STAGING_BASE_PATH", "/staging")
