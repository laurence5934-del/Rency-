ffrom app.broker.ibkr_official import test_connection as check_ibkr_connection


def test_connection():
    result = check_ibkr_connection()

    assert isinstance(result, dict)
    assert "connected" in result
    assert "errors" in result