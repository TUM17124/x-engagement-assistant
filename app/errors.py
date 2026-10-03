import httpx

class ServiceError(RuntimeError):
    def __init__(self, service, status=0, retry_after=0):
        self.service, self.status, self.retry_after = service, status, retry_after
        messages = {
            400: f"{service} rejected this request. Check the content, target and selected model or action before trying again.",
            408: f"{service} timed out. Try again later or choose another model.",
            500: f"{service} is temporarily unavailable. Try again later.",
            502: f"{service} is temporarily unavailable. Try again later.",
            503: f"{service} is temporarily unavailable. Try again later.",
            504: f"{service} timed out. Try again later.",
            404: f"The requested {service} item or endpoint is unavailable. Check the target or use the manual workflow.",
            401: f"Your {service} credentials are invalid or expired. Reconnect or replace the key in Settings.",
            402: ("Your current X API project does not have credits/access for this endpoint." if service == "X"
                  else f"Your {service} provider needs credits or billing access. Check your provider account."),
            403: f"Your {service} account does not have permission for this action.",
            429: f"{service} rate limit reached. Requests are paused until the limit resets.",
        }
        if service == "OpenAI API Key" and status == 401:
            messages[401] = "OpenAI API Key mode rejected the saved API key. Your ChatGPT login is separate. Select ChatGPT Plan in Settings to use your connected plan, or replace the API key for API billing."
        if service == "X" and status == 402:
            messages[402] += " ChatGPT plan usage does not pay X API costs. Use Open Search on X for discovery or Copy & open manually for publishing."
        if status == 403:
            messages[403] += " Reconnect with the required permissions or use the manual workflow."
        if status == 429:
            messages[429] += " Wait before retrying; no automatic publishing retry was made."
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
