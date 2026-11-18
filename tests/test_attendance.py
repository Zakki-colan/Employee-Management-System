
def test_attendance_check_in(client):
    response = client.post("/attendance/check-in")

    assert response.status_code in [200, 201, 401, 403]


def test_get_my_attendance(client):
    response = client.get("/attendance/my-attendance")

    assert response.status_code in [200, 401, 403]
