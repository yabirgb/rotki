def test_connection(database):
    assert hasattr(database, 'writer_client') is True