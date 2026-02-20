
from workers import Response
from auth.sessions import require_user_id

async def create_todo(env, request):
    user_id = await require_user_id(env, request)
    if not user_id:
        return Response("Unauthorized", status=401)

    ct = request.headers.get("content-type", "")
    if "application/json" not in ct:
        return Response("Unsupported Media Type", status=415)

    try:
        body = await request.json()
    except Exception:
        return Response("Invalid JSON body", status=400)

    text = (body.get("text") or "").strip()
    if not text:
        return Response("Missing 'text'", status=400)

    # Insert
    res = await env.DB.prepare(
        "INSERT INTO todos (user_id, text) VALUES (?, ?)"
    ).bind(user_id, text).run()

    # D1 run() result is often a JsProxy; convert defensively
    res = res.to_py() if hasattr(res, "to_py") else res

    todo_id = res.get("meta", {}).get("last_row_id")
    return Response.json({"id": todo_id, "text": text, "completed": False}, status=201)

async def list_todos(env, request):
    user_id = await require_user_id(env, request)
    if not user_id:
        return Response("Unauthorized", status=401)

    # List newest first
    result = await env.DB.prepare(
        """
        SELECT id, text, completed, created_at
        FROM todos
        WHERE user_id = ?
        ORDER BY created_at DESC, id DESC
        """
    ).bind(user_id).all()

    result = result.to_py() if hasattr(result, "to_py") else result
    rows = result.get("results", [])

    # Normalize completed 0/1 -> bool
    todos = [
        {
            "id": r["id"],
            "text": r["text"],
            "completed": bool(r["completed"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]

    return Response.json({"todos": todos})



async def update_todo(env, request, todo_id: int):
    user_id = await require_user_id(env, request)
    if not user_id:
        return Response("Unauthorized", status=401)

    ct = request.headers.get("content-type", "")
    if "application/json" not in ct:
        return Response("Unsupported Media Type", status=415)

    try:
        body = await request.json()
    except Exception:
        return Response("Invalid JSON body", status=400)

    # Allow partial updates
    new_text = body.get("text", None)
    completed = body.get("completed", None)

    sets = []
    args = []

    if new_text is not None:
        new_text = (new_text or "").strip()
        if not new_text:
            return Response("Invalid 'text'", status=400)
        sets.append("text = ?")
        args.append(new_text)

    if completed is not None:
        sets.append("completed = ?")
        args.append(1 if bool(completed) else 0)

    if not sets:
        return Response("No fields to update", status=400)

    args.extend([todo_id, user_id])

    res = await env.DB.prepare(
        f"""
        UPDATE todos
        SET {", ".join(sets)}
        WHERE id = ? AND user_id = ?
        """
    ).bind(*args).run()

    res = res.to_py() if hasattr(res, "to_py") else res
    changed = res.get("meta", {}).get("changes", 0)
    if changed == 0:
        return Response("Not Found", status=404)

    return Response.json({"ok": True})

async def delete_todo(env, request, todo_id: int):
    user_id = await require_user_id(env, request)
    if not user_id:
        return Response("Unauthorized", status=401)

    res = await env.DB.prepare(
        "DELETE FROM todos WHERE id = ? AND user_id = ?"
    ).bind(todo_id, user_id).run()

    res = res.to_py() if hasattr(res, "to_py") else res
    changed = res.get("meta", {}).get("changes", 0)
    if changed == 0:
        return Response("Not Found", status=404)

    return Response("", status=204)