import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from workers import Response
from auth.cookies import parse_cookies, make_session_cookie, clear_session_cookie

SESSION_TTL_SECONDS = 3600

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

async def create_session(env, user_id: int):
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)

    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=SESSION_TTL_SECONDS)
    expires_iso = expires.strftime("%Y-%m-%d %H:%M:%S")

    await env.DB.prepare(
        "INSERT INTO sessions (user_id, token_hash, expires_at) VALUES (?, ?, ?)"
    ).bind(user_id, token_hash, expires_iso).run()

    cookie = make_session_cookie(token, SESSION_TTL_SECONDS)
    return Response.json({"ok": True}, headers={"Set-Cookie": cookie})

async def revoke_session(env, request):
    cookies = parse_cookies(request.headers.get("cookie", ""))
    token = cookies.get("session")

    if token:
        token_hash = _hash_token(token)
        await env.DB.prepare("DELETE FROM sessions WHERE token_hash = ?").bind(token_hash).run()

    return Response("", status=204, headers={"Set-Cookie": clear_session_cookie()})


async def require_user_id(env, request):
    user = await _acquire_user_row(env, request)
    if user is None: 
        return None
    return user['id']
async def require_username(env, request):
    user = await _acquire_user_row(env, request)
    if user is None: 
        return None

    return user['username']

async def _acquire_user_row(env, request):
    cookies = parse_cookies(request.headers.get("cookie", ""))
    token = cookies.get("session")
    if not token:
        return None

    token_hash = _hash_token(token)
    row = await env.DB.prepare(
        """
        SELECT users.id, users.username
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.token_hash = ?
          AND sessions.expires_at > datetime('now')
        """
    ).bind(token_hash).first()

    if row is None:
        return None

    return row.to_py()
