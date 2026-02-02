"""Fixtures for mill processors tests."""

import os
from uuid import uuid4

# Set up environment variables for MillContext before any imports
os.environ.setdefault("QUARANTINE_WAREHOUSE_ID", str(uuid4()))
os.environ.setdefault("STAGING_WAREHOUSE_ID", str(uuid4()))
os.environ.setdefault("QUARANTINE_BASE_PATH", "/quarantine")
os.environ.setdefault("STAGING_BASE_PATH", "/staging")
