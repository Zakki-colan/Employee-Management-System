def test_get_employees(client):
    response = client.get("/employees")

    assert response.status_code == 401

def test_get_employee_requires_authentication(client):
    response = client.get("/employees/999")

    assert response.status_code == 401
    assert response.json() == {
        "message": "Invalid or expired authentication token",
        "success": False,
        "status_code": 401,
        "data": {},
    }


def test_invalid_request_returns_frontend_friendly_validation_error(client):
    response = client.post("/auth/login", json={"email": "invalid"})

    assert response.status_code == 400
    body = response.json()
    assert body["message"] == "Please check the submitted information."
    assert body["data"]["errors"][0]["field"] == "body.password"
    assert body["data"]["errors"][0]["message"]