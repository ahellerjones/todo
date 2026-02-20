import db.todos as todo
import re

async def handle_todos(env, request, url: str, method: str):
    m = re.match(r".*/api/todos/(\d+)$", url)
    if m:
        todo_id = int(m.group(1))
        if method == "PATCH":
            return await todo.update_todo(env, request, todo_id)
        if method == "DELETE":
            return await todo.delete_todo(env, request, todo_id)

    if url.endswith("/api/todos"):
        if method == "POST":
            return await todo.create_todo(env, request)
        if method == "GET":
            return await todo.list_todos(env, request)

    return None