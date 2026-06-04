import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_db_connection():
    """Mock psycopg2 connection"""
    conn = MagicMock()
    conn.closed = False
    return conn

@pytest.fixture
def mock_db_handler(mock_db_connection, monkeypatch):
    """Mock DBHandler with predefined behavior"""
    from pipeline.utils.db_handler import DBHandler
    
    handler = DBHandler()
    handler.connection = mock_db_connection
    
    # Mock connect to avoid real DB connection
    monkeypatch.setattr(handler, "connect", lambda: None)
    return handler

@pytest.fixture
def mock_minio_client():
    """Mock Minio client"""
    client = MagicMock()
    return client

@pytest.fixture
def mock_mqtt_client():
    """Mock MQTT client"""
    client = MagicMock()
    return client
