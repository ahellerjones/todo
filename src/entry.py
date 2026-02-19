from workers import Response, WorkerEntrypoint
from submodule import get_hello_message
class Default(WorkerEntrypoint):
    async def fetch(self, request):
        if request.method != "POST":
                return Response("Method Not Allowed", status=405)

        content_type = request.headers.get("content-type", "")
        if "application/json" not in content_type:
            return Response("Unsupported Media Type", status=415)

        try:
            body = await request.json()
        except Exception:
            return Response("Invalid JSON body", status=400)

        name = body.get("name")
        if not name:
            return Response("Missing 'name' field", status=400)

        return Response.json({
            "message": f"Hello, {name}!"
        })
