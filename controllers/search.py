from fastapi import Request
import starlette.status as status
from google.cloud import firestore
from google.auth.transport import requests
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

from firebase.helpers import validateFirebaseToken

firebase_request_adapter = requests.Request()
firestore_db = firestore.Client()

async def run_search(request: Request, templates: Jinja2Templates):
    query = request.query_params.get("q", "").strip().lower()

    if not query:
        return RedirectResponse(url="/?error=Search+query+missing", status_code=status.HTTP_400_BAD_REQUEST)

    try:
        # Search users by Username (case-insensitive prefix match)
        users_query = (
            firestore_db.collection("User")
            .where("Username", ">=", query)
            .where("Username", "<=", query + "\uf8ff")
        )
        users = [{"id": doc.id, **doc.to_dict()} for doc in users_query.stream()]

        return templates.TemplateResponse("search.html", {"request": request, "users": users, "q": query })
    except Exception as e:
        return HTMLResponse(f"Search failed: {str(e)}", status_code=500)