import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
# from pyodide.ffi import to_py


from workers import Response, WorkerEntrypoint

PBKDF2_ITERS = 150_000  # reasonable baseline; tune as needed

SESSION_TTL_SECONDS = 3600  # 1 hour

def _hash_password(password: str) -> str:
    # Store as: pbkdf2_sha256$iters$salt_b64$dk_b64
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERS, dklen=32)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(dk).decode("ascii"),
    )

def _verify_password(stored: str, password: str) -> bool:
    # stored format: pbkdf2_sha256$iters$salt_b64$dk_b64
    try:
        algo, iters_s, salt_b64, dk_b64 = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iters = int(iters_s)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(dk_b64)
        derived = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iters, dklen=len(expected)
        )
        return hmac.compare_digest(derived, expected)
    except Exception:
        return False

def _hash_session_token(token: str) -> str:
    # Hash token before storing in DB
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def _http_date(dt: datetime) -> str:
    # RFC-ish for Expires=; not strictly required if you use Max-Age.
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = request.url  # string
        method = request.method.upper()

        # crude routing (fine for now)
        if method == "POST" and url.endswith("/api//users"):
            return await self._create_user(request)

        if method == "POST" and url.endswith("/api/login"):
            return await self._login(request)
        
        if method == "GET" and url.endswith("/api/me"):
            return await self._me(request)


        return Response("Not Found", status=404)



    async def _create_user(self, request):
        ct = request.headers.get("content-type", "")
        if "application/json" not in ct:
            return Response("Unsupported Media Type", status=415)

        try:
            body = await request.json()
        except Exception:
            return Response("Invalid JSON body", status=400)

        username = (body.get("username") or "").strip()
        password = body.get("password") or ""

        if not username or not password:
            return Response("Missing username or password", status=400)

        pw_hash = _hash_password(password)

        try:
            # D1 is available as self.env.DB when binding name is "DB" :contentReference[oaicite:2]{index=2}
            stmt = self.env.DB.prepare(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)"
            ).bind(username, pw_hash)
            await stmt.run()
        except Exception:
            # simplest: assume uniqueness violation or db error
            return Response("Username already exists (or DB error)", status=409)

        return Response.json({"ok": True, "username": username}, status=201)


    async def _login(self, request):
        ct = request.headers.get("content-type", "")
        if "application/json" not in ct:
            return Response("Unsupported Media Type", status=415)

        try:
            body = await request.json()
        except Exception:
            return Response("Invalid JSON body", status=400)

        username = (body.get("username") or "").strip()
        password = body.get("password") or ""
        if not username or not password:
            return Response("Missing username or password", status=400)

        # Look up user
        row = await self.env.DB.prepare(
            "SELECT id, password_hash FROM users WHERE username = ?"
        ).bind(username).first()

        row = row.to_py()  # <-- convert JsProxy -> Python dict

        if not row or not _verify_password(row["password_hash"], password):
            # Keep message generic
            return Response("Invalid credentials", status=401)

        user_id = row["id"]

        # Create session token (opaque)
        token = secrets.token_urlsafe(32)
        token_hash = _hash_session_token(token)

        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=SESSION_TTL_SECONDS)
        expires_iso = expires.strftime("%Y-%m-%d %H:%M:%S")  # SQLite datetime('now') style

        # Store hashed token with expiry
        await self.env.DB.prepare(
            "INSERT INTO sessions (user_id, token_hash, expires_at) VALUES (?, ?, ?)"
        ).bind(user_id, token_hash, expires_iso).run()

        # Set cookie
        cookie = (
            f"session={token}; "
            f"HttpOnly; Secure; SameSite=Lax; Path=/; "
            f"Max-Age={SESSION_TTL_SECONDS}"
        )

        # Response
        cookie = f"session={token}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age={SESSION_TTL_SECONDS}"
        return Response.json({"ok": True}, headers={"Set-Cookie": cookie})


    async def _me(self, request):

        # Extract session cookie
        cookie_header = request.headers.get("cookie", "")
        cookies = {}
        for part in cookie_header.split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                cookies[k] = v

        token = cookies.get("session")
        if not token:
            return Response("Unauthorized", status=401)

        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

        # Look up valid session
        row = await self.env.DB.prepare(
            """
            SELECT users.username
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ?
            AND sessions.expires_at > datetime('now')
            """
        ).bind(token_hash).first()

        if row is None:
            return Response("Unauthorized", status=401)

        row = row.to_py()  # convert JsProxy → Python dict

        return Response.json({
            "message": f"Hello, {row['username']}!"
        })