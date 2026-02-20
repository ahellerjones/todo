def parse_cookies(cookie_header: str) -> dict:
    cookies = {}
    for part in (cookie_header or "").split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            cookies[k] = v
    return cookies

def make_session_cookie(token: str, max_age_seconds: int) -> str:
    return (
        f"session={token}; "
        f"HttpOnly; Secure; SameSite=Lax; Path=/; "
        f"Max-Age={max_age_seconds}"
    )

def clear_session_cookie() -> str:
    return (
        "session=; "
        "HttpOnly; Secure; SameSite=Lax; Path=/; "
        "Max-Age=0"
    )