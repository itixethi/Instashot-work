from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from google.auth.transport import requests

from firebase.helpers import validateFirebaseToken

firebase_request_adapter = requests.Request()

async def login(request: Request, templates: Jinja2Templates):
    try:
        id_token_cookie = request.cookies.get("token")
        user_token = validateFirebaseToken(id_token=id_token_cookie, firebase_request_adapter=firebase_request_adapter)
        isAuthorized = user_token is not None

        # Check if logout query flag is present
        logged_out = request.query_params.get("logged_out", "false").lower() == "true"

        return templates.TemplateResponse(request=request, name="login.html", context={"isAuthorized": isAuthorized, "request": request, "logged_out": logged_out})
    except Exception as e:
        return HTMLResponse(str(e), status_code=500)
    
async def register(request: Request, templates: Jinja2Templates):
    try: 
        id_token = request.cookies.get("token")
        user_token = validateFirebaseToken(id_token, firebase_request_adapter)
        isAuthorized = user_token is not None
        
        return templates.TemplateResponse(request=request, name="registration.html", context={"isAuthorized": isAuthorized, "request": request})
    except Exception as e:
        return HTMLResponse(str(e), status_code=500)