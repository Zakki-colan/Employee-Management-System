
from locust import HttpUser, task, between


class EMSUser(HttpUser):

    wait_time = between(1, 3)

    def on_start(self):

        response = self.client.post(
            "/auth/login",
            json={
                "email": "admin@example.com",
                "password": "your_password"
            }
        )

        if response.status_code == 200:
            token = response.json()["access_token"]

            self.client.headers.update({
                "Authorization": f"Bearer {token}"
            })

    @task(3)
    def get_employees(self):
        self.client.get("/employees/")

    @task(2)
    def get_departments(self):
        self.client.get("/departments/")

    @task(2)
    def get_attendance(self):
        self.client.get("/attendance/")

    @task(1)
    def get_leaves(self):
        self.client.get("/leaves/")
