from fastapi import FastAPI, Request 
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from google.cloud import firestore 
from google.auth.transport import requests
from fastapi import UploadFile, Form

from controllers.authentication import login, register
from firebase.helpers import validateFirebaseToken
from controllers.users import show_profile, follow_user, unfollow_user, show_select_handle_page, select_handle, show_following, show_followers
from controllers.post import show_upload_form, upload_post
from controllers.search import run_search
from controllers.post import upload_profile_image, add_comment

# call the api builder 
app = FastAPI()
firestore_db = firestore.Client()
firebase_request_adapter = requests.Request()

# Mount static files and set up Jinja2 templates 
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def getUser(user_token):
    user_id = user_token['user_id']
    user_ref = firestore_db.collection("User").document(user_id)

    user_snapshot = user_ref.get()

    if not user_snapshot.exists:
        user_data = {"Username": user_token.get("name", "Unknown"), "age": 0, "email": user_token.get("email", "")}
        user_ref.set(user_data)

        # Initialize empty 'followers' and 'following' subcollections
        followers_ref = user_ref.collection("followers")
        following_ref = user_ref.collection("following")

        followers_ref.document("_init").set({"init": True})
        followers_ref.document("_init").delete()

        following_ref.document("_init").set({"init": True})
        following_ref.document("_init").delete()

    return user_ref

def checkAndReturnUser(id_token):
    user_token = validateFirebaseToken(id_token=id_token, firebase_request_adapter=firebase_request_adapter)
    return getUser(user_token) if user_token else None

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    try:
        id_token_cookie = request.cookies.get("token")
        user_token = validateFirebaseToken(id_token=id_token_cookie, firebase_request_adapter=firebase_request_adapter)
        isAuthorized = user_token is not None

        posts = []
        user_data = None
        viewer_id = None
        suggested_users = []

        if user_token:
            viewer_id = user_token['user_id']
            user_doc = firestore_db.collection("User").document(viewer_id).get()

            # Redirect to /select-handle if Username is missing
            if not user_doc.exists or 'Username' not in user_doc.to_dict():
                return RedirectResponse(url="/select-handle", status_code=307)

            user_data = user_doc.to_dict()
            user_data['id'] = viewer_id

            # Collect all user ID, self and following
            following_ref = firestore_db.collection("User").document(viewer_id).collection("following").stream()
            following_ids = [doc.id for doc in following_ref]
            user_ids = following_ids + [viewer_id]

            # Fetch posts from current user + following
            all_posts = firestore_db.collection("Post") \
                .order_by("Date", direction=firestore.Query.DESCENDING) \
                .limit(100).stream()  # Fetch more, filter locally

            for doc in all_posts:
                post_data = doc.to_dict()
                if post_data.get("UserID") in user_ids:
                    post_data["id"] = doc.id

                    # Fetch comments (newest first, up to 100)
                    comments_ref = firestore_db.collection("Post").document(doc.id).collection("Comments") \
                        .order_by("timestamp", direction=firestore.Query.DESCENDING).limit(100).stream()
                    post_data["comments"] = [c.to_dict() for c in comments_ref]

                    posts.append(post_data)

            posts = posts[:50]  # Trim after filtering

            # Fetch suggested users (exclude self and already-followed)
            all_users = firestore_db.collection("User").where("Username", "!=", None).limit(20).stream()
            for doc in all_users:
                data = doc.to_dict()
                if doc.id != viewer_id and doc.id not in following_ids:
                    data["id"] = doc.id
                    suggested_users.append(data)

        return templates.TemplateResponse(request=request, name="index.html", context={"isAuthorized": isAuthorized, "request": request, "posts": posts, "user": user_data, "suggested_users": suggested_users})
    except Exception as e:
        return HTMLResponse(str(e), status_code=500)

@app.get("/login", response_class=HTMLResponse)
async def handleLoginRoute(request: Request):
    return await login(request=request, templates=templates)

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("token")
    return response

@app.get("/register", response_class=HTMLResponse)
async def handle_register_page(request: Request):
    return await register(request=request, templates=templates)

@app.get("/profile/{username}", response_class=HTMLResponse)
async def handle_profile(username: str, request: Request):
    return await show_profile(username=username, request=request, templates=templates)

@app.post("/comment", response_class=RedirectResponse)
async def handle_comment_post(request: Request):
    return await add_comment(request=request)

@app.get("/follow-user", response_class=RedirectResponse)
async def handle_follow_user(request: Request):
    return await follow_user(request=request)
    
@app.get("/unfollow-user", response_class=RedirectResponse)
async def handle_unfollow_user(request: Request):
    return await unfollow_user(request=request)

@app.get("/upload-post", response_class=HTMLResponse)
async def handle_show_upload_form(request: Request):
    return await show_upload_form(request=request, templates=templates)

@app.post("/upload-profile-image", response_class=RedirectResponse)
async def handle_upload_profile_image(request: Request, file: UploadFile = Form(...)):
    return await upload_profile_image(request=request, file=file)

@app.get("/profile/{username}/followers", response_class=HTMLResponse)
async def view_followers(username: str, request: Request):
    return await show_followers(username=username, request=request, templates=templates)

@app.get("/profile/{username}/following", response_class=HTMLResponse)
async def view_following(username: str, request: Request):
    return await show_following(username=username, request=request, templates=templates)

@app.post("/upload-post", response_class=RedirectResponse)
async def handle_upload_post(request: Request):
    return await upload_post(request=request)

@app.get("/search", response_class=HTMLResponse)
async def handle_search(request: Request):
    return await run_search(request=request, templates=templates)

@app.get("/select-handle", response_class=HTMLResponse)
async def handle_select_handle_page(request: Request):
    return await show_select_handle_page(request=request, templates=templates)
    
@app.post("/select-handle", response_class=RedirectResponse)
async def handle_select_handle_post(request: Request):
    return await select_handle(request=request)