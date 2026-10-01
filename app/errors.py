import httpx

class ServiceError(RuntimeError):
    def __init__(self, service, status=0, retry_after=0):
        self.service, self.status, self.retry_after = service, status, retry_after
        messages = {
            401: f"Your {service} credentials are invalid or expired. Reconnect or replace the key in Settings.",
            402: ("Your current X API project does not have credits/access for this endpoint." if service == "X"
                  else f"Your {service} provider needs credits or billing access. Check your provider account."),
            403: f"Your {service} account does not have permission for this action.",
            429: f"{service} rate limit reached. Requests are paused until the limit resets.",
        }
        super().__init__(messages.get(status, f"Could not reach {service}. Check your connection and try again."))
    def details(self):
        return {"error": str(self), "technical": f"{self.service} HTTP {self.status}" if self.status else self.service + " connection failed",
                "retry_after": self.retry_after}

def check_response(response, service):
    if response.status_code >= 400:
        import time
        try:
            retry = max(int(response.headers.get("retry-after", 0)),
                        int(response.headers.get("x-rate-limit-reset", 0)) - int(time.time()), 60)
        except ValueError:
            retry = 900
        raise ServiceError(service, response.status_code, retry)

async def request(client, method, url, service, **kwargs):
    try:
        response = await client.request(method, url, **kwargs)
    except httpx.RequestError:
        raise ServiceError(service) from None
    check_response(response, service)
    return response
