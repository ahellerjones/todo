from workers import Response
from auth.pw import verify_password
from auth.sessions import create_session, revoke_session, require_username
from db.users import create_user, get_user_by_username

async def handle_auth(env, request, url: str, method: str):
    if url.endswith("/api/users") and method == "POST":
        return await signup(env, request)

    if url.endswith("/api/login") and method == "POST":
        return await login(env, request)

    if url.endswith("/api/logout") and method == "POST":
        return await logout(env, request)

    if url.endswith("/api/me") and method == "GET":
        return await me(env, request)

    return None

async def signup(env, request):
    body = await request.json()
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    if not username or not password:
        return Response.json({"error": "Missing username or password"}, status=400)

    try:
        await create_user(env, username, password)
    except Exception:
        return Response.json({"error": "Username already exists"}, status=409)

    return Response.json({"ok": True}, status=201)

async def login(env, request):
    body = await request.json()
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    row = await get_user_by_username(env, username)
    if not row:
        return Response.json({"error": "Invalid credentials"}, status=401)

    if not verify_password(row["password_hash"], password):
        return Response.json({"error": "Invalid credentials"}, status=401)

    # sets cookie + inserts session
    return await create_session(env, user_id=row["id"])

async def logout(env, request):
    return await revoke_session(env, request)

async def me(env, request):
    user = await require_username(env, request)
    if not user:
        return Response("Unauthorized", status=401)
    return Response.json({"message": f"Hello, {user}!"})