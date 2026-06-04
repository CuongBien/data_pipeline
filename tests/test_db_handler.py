import pytest
from unittest.mock import MagicMock, call

def test_db_handler_connect_success(mock_db_handler, mock_db_connection):
    """Test connect method sets connection property"""
    # Note: connect is mocked to avoid real connection in mock_db_handler fixture
    # We can just verify it holds a connection
    assert mock_db_handler.connection is not None
    assert mock_db_handler.connection.closed == False

def test_get_records_by_status(mock_db_handler, mock_db_connection):
    mock_cursor = MagicMock()
    mock_db_connection.cursor.return_value.__enter__.return_value = mock_cursor
    
    # Mock row description and fetchall
    mock_cursor.description = [("id",), ("camera_id",), ("status",)]
    mock_cursor.fetchall.return_value = [(1, "cam1", "NEW")]
    
    records = mock_db_handler.get_records_by_status("NEW")
    
    assert len(records) == 1
    assert records[0]["id"] == 1
    assert records[0]["status"] == "NEW"

def test_update_status(mock_db_handler, mock_db_connection):
    mock_cursor = MagicMock()
    mock_db_connection.cursor.return_value.__enter__.return_value = mock_cursor
    
    mock_db_handler.update_status([1, 2, 3], "PROCESSING")
    
    mock_cursor.execute.assert_called_once()
    args, kwargs = mock_cursor.execute.call_args
    assert "UPDATE" in args[0]
    assert "PROCESSING" in args[1]
    assert (1, 2, 3) in args[1]
