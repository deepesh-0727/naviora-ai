from locust import HttpUser, task, between

class NavioraUser(HttpUser):
    wait_time = between(1, 5)

    @task(3)
    def check_health(self):
        self.client.get("/health")

    @task(1)
    def get_doctors(self):
        self.client.get("/api/v1/doctors/")

    @task(2)
    def check_wait_time(self):
        # Assuming doctor ID 1 exists from init_db
        self.client.get("/api/v1/queue/wait-time/1?position=5")

    @task(1)
    def navigation_route(self):
        self.client.post("/api/v1/navigation/route?start_node=G_ENTRANCE&end_node=F1_CARDIOLOGY")
