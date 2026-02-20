from auth.pw import hash_password

async def get_user_by_username(env, username: str):
    row = await env.DB.prepare(
        "SELECT id, username, password_hash FROM users WHERE username = ?"
    ).bind(username).first()

    return row.to_py() if hasattr(row, "to_py") else row

async def create_user(env, username: str, password: str):
    pw_hash = hash_password(password)
    await env.DB.prepare(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)"
    ).bind(username, pw_hash).run()