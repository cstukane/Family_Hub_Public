# HTTP Status Codes
HTTP_OK = 200


def test_index_route(client):
    """Test the index route."""
    response = client.get("/")
    assert response.status_code == HTTP_OK
    assert b"Kitchen Hub" in response.data


def test_health_route(client):
    """Test the health check route."""
    response = client.get("/health")
    assert response.status_code == HTTP_OK

    data = response.get_json()
    assert "status" in data
    assert data["status"] == "ok"
    assert "time" in data
    assert "versions" in data
    assert "app" in data["versions"]
    assert "platform" in data
    assert "python_version" in data


def test_view_route(client):
    """Test the view route."""
    response = client.get("/view/calendar")
    assert response.status_code == HTTP_OK
    assert b"Kitchen Hub" in response.data

    response = client.get("/view/media")
    assert response.status_code == HTTP_OK
    assert b"Kitchen Hub" in response.data


def test_cooking_view_route(client):
    """Test the cooking view route."""
    response = client.get("/view/cooking")
    assert response.status_code == HTTP_OK
    assert b"Cooking Mode" in response.data
    assert b"cooking-content" in response.data
