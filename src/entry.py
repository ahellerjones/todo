import base64
import hashlib
import hmac
import secrets

from workers import Response, WorkerEntrypoint

PBKDF2_ITERS = 150_000  # reasonable baseline; tune as needed

def _hash_password(password: str) -> str:
    # Store as: pbkdf2_sha256$iters$salt_b64$dk_b64
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERS, dklen=32)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(dk).decode("ascii"),
    )

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = request.url  # string
        method = request.method.upper()

        # crude routing (fine for now)
        if method == "POST" and url.endswith("/users"):
            return await self._create_user(request)

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
