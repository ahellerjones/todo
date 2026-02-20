from datetime import datetime, timedelta, timezone
# from pyodide.ffi import to_py

from workers import WorkerEntrypoint, Response
from routes.auth import handle_auth
from routes.todos import handle_todos

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = request.url
        method = request.method.upper()

        # route to auth endpoints
        resp = await handle_auth(self.env, request, url, method)
        if resp is not None:
            return resp

        # route to todo endpoints
        resp = await handle_todos(self.env, request, url, method)
        if resp is not None:
            return resp

        return Response("Not Found", status=404)
