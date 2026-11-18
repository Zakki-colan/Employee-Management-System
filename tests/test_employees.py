def test_get_employees(client):
    response = client.get("/employees")

    assert response.status_code == 401

def test_get_employee_not_found(client):
    response = client.get("/employees/999")

    assert response.status_code == 401
    assert response.json() == {
        "message": "Invalid or expired authentication token",
        "errors": [],
    }


def test_invalid_request_returns_frontend_friendly_validation_error(client):
    response = client.post("/auth/login", json={"email": "invalid"})

    assert response.status_code == 422
    body = response.json()
    assert body["message"] == "Please check the submitted information."
    assert body["errors"][0]["field"] == "body.password"
    assert body["errors"][0]["message"]