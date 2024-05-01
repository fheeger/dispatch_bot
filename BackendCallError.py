class BackendCallError(RuntimeError):
    def __init__(self, http_response):
        self.error_status = http_response.status_code
        body = http_response.json()

        self.error_type = body["error_type"]
        self.message = body["message"]

    def __str__(self):
        return f"{self.error_type}: {self.message}"
