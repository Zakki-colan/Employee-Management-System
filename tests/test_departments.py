def test_get_departments(client):
    response = client.get("/departments")

    assert response.status_code == 200

def test_get_department_not_found(client):
    response = client.get("/departments/999")

    assert response.status_code == 404