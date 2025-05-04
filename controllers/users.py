from fastapi import Request
from google.cloud import firestore
from fastapi.responses import HTMLResponse, RedirectResponse
from google.auth.transport import requests
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette import status

from firebase.helpers import validateFirebaseToken

firebase_request_adapter = requests.Request()
firestore_db = firestore.Client()

def get_login_status(request: Request, firebase_request_adapter):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token=id_token, firebase_request_adapter=firebase_request_adapter)
    return id_token, user_token, user_token is not None

def get_user_profile(user):
    user_query = firestore_db.collection('User').where('user_id', '==', user['user_id']).limit(1).get()
    if user_query:
        user_doc = user_query[0]
        if user_doc is not None and user_doc.exists:  # Enhanced check for user_doc
            user_data = user_doc.to_dict()
            if user_data:
                user_data['id'] = user_doc.id  # Include the document ID in the returned data
                return user_data
    return None

async def show_profile(request: Request, username: str, templates: Jinja2Templates):
    try:
        # Validate user session
        id_token_cookie = request.cookies.get("token")
        user_token = validateFirebaseToken(id_token=id_token_cookie, firebase_request_adapter=firebase_request_adapter)
        isAuthorized = user_token is not None

        if not isAuthorized:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        viewer_id = user_token["user_id"]

        # Fetch the target user
        user_query = firestore_db.collection('User').where('Username', '==', username).limit(1)
        user_snapshot = next(user_query.stream(), None)

        if not user_snapshot or not user_snapshot.exists:
            return RedirectResponse(url="/?error=User+not+found", status_code=status.HTTP_404_NOT_FOUND)

        user_data = user_snapshot.to_dict()
        user_data['id'] = user_snapshot.id

        # Determine if this is the viewer's own profile
        is_own_profile = (user_data['id'] == viewer_id)

        # Follow status (only check if not own profile)
        following = False
        if not is_own_profile:
            follow_ref = firestore_db.collection("User").document(viewer_id).collection("following").document(user_data["id"])
            following = follow_ref.get().exists

        # Posts by this user
        posts_ref = firestore_db.collection('Post') \
            .where('Username', '==', username) \
            .order_by('Date', direction=firestore.Query.DESCENDING)

        posts = [{"id": doc.id, **doc.to_dict()} for doc in posts_ref.stream()]

        # Is viewer following this user?
        follow_doc = firestore_db.collection("User") \
            .document(viewer_id).collection("following") \
            .document(user_data["id"]).get()
        following = follow_doc.exists

        # Count followers and following
        follower_count = sum(1 for _ in firestore_db.collection("User").document(user_data['id']).collection("followers").stream())
        following_count = sum(1 for _ in firestore_db.collection("User").document(user_data['id']).collection("following").stream())

        # Suggested users (excluding current profile and viewer)
        user_docs = firestore_db.collection("User") \
            .where("Username", "!=", None).limit(10).stream()

        suggested_users = []
        for doc in user_docs:
            data = doc.to_dict()
            uid = doc.id
            if uid != user_data['id'] and uid != viewer_id:
                data = doc.to_dict()
                data["id"] = uid
                follow_check = firestore_db.collection("User").document(viewer_id).collection("following").document(uid).get()
                data["is_following"] = follow_check.exists
                suggested_users.append(data)

        return templates.TemplateResponse("profile.html", {"request": request, "isAuthorized": isAuthorized, "user": user_data, "posts": posts, "follower_count": follower_count, "following_count": following_count, "following": following, "suggested_users": suggested_users, "is_own_profile": is_own_profile})
    except Exception as e:
        return HTMLResponse(f"<h1>Error: {str(e)}</h1>", status_code=500)
    
async def follow_user(request: Request):
    try:
        id_token_cookie = request.cookies.get("token")
        user_token = validateFirebaseToken(id_token=id_token_cookie, firebase_request_adapter=firebase_request_adapter)
        if not user_token:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

        user_id = user_token["user_id"]
        profile_id_to_follow = request.query_params.get("profile_id")
        username = request.query_params.get("username")

        if not profile_id_to_follow:
            return RedirectResponse(url="/?error=Profile+ID+missing", status_code=status.HTTP_400_BAD_REQUEST)

        if user_id == profile_id_to_follow:
            return RedirectResponse(url="/?error=You+cannot+follow+yourself", status_code=status.HTTP_400_BAD_REQUEST)

        # Add follow entry
        firestore_db.collection("User").document(user_id).collection("following").document(profile_id_to_follow).set({"following": True})
        firestore_db.collection("User").document(profile_id_to_follow).collection("followers").document(user_id).set({"follower": True})

        print(f"{user_id} followed {profile_id_to_follow}")

        # If username not passed, try to fetch it
        if not username:
            followed_user_doc = firestore_db.collection("User").document(profile_id_to_follow).get()
            if followed_user_doc.exists:
                username = followed_user_doc.to_dict().get("Username")

        # Fallback redirect
        redirect_url = f"/profile/{username}" if username else "/"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        return HTMLResponse(f"<h1>Error: {str(e)}</h1>", status_code=500)
    
async def unfollow_user(request: Request):
    try:
        id_token_cookie = request.cookies.get("token")
        user_token = validateFirebaseToken(id_token=id_token_cookie, firebase_request_adapter=firebase_request_adapter)
        if not user_token:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

        user_id = user_token["user_id"]
        profile_id_to_unfollow = request.query_params.get("profile_id")
        username = request.query_params.get("username") 

        if not profile_id_to_unfollow:
            return RedirectResponse(url="/?error=Profile+ID+missing", status_code=status.HTTP_400_BAD_REQUEST)
        
        if user_id == profile_id_to_unfollow:
            return RedirectResponse(url="/?error=You+cannot+unfollow+yourself", status_code=status.HTTP_400_BAD_REQUEST)

        # Delete from following list of current user
        firestore_db.collection("User") \
            .document(user_id).collection("following") \
            .document(profile_id_to_unfollow).delete()

        # Delete from followers list of the target user
        firestore_db.collection("User") \
            .document(profile_id_to_unfollow).collection("followers") \
            .document(user_id).delete()

        print(f"{user_id} unfollowed {profile_id_to_unfollow}")

        redirect_url = f"/profile/{username}" if username else "/"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {str(e)}</h1>", status_code=500)

async def show_select_handle_page(request: Request, templates: Jinja2Templates):
    try:
        _, _, is_logged_in = get_login_status(request, firebase_request_adapter)
        if not is_logged_in:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

        return templates.TemplateResponse("select-handle.html", {"request": request, "isAuthorized": is_logged_in})
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {str(e)}</h1>", status_code=500)

async def select_handle(request: Request):
    try:
        _, user_token, is_logged_in = get_login_status(request, firebase_request_adapter)
        if not is_logged_in or user_token is None:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

        form_data = await request.form()
        handle = form_data.get("handle", "").strip()

        # Check if Username already exists
        existing = firestore_db.collection("User").where("Username", "==", handle).limit(1).stream()
        if any(existing):
            return RedirectResponse(url="/select-handle?error=Handle+already+taken", status_code=status.HTTP_303_SEE_OTHER)

        user_id = user_token["user_id"]
        user_ref = firestore_db.collection("User").document(user_id)
        user_ref.set({"Username": handle}, merge=True)

        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {str(e)}</h1>", status_code=500)
    
async def show_following(request: Request, username: str, templates: Jinja2Templates):
    user_query = firestore_db.collection('User').where('Username', '==', username).limit(1)
    user_snapshot = next(user_query.stream(), None)

    if not user_snapshot or not user_snapshot.exists:
        return HTMLResponse(f"User not found", status_code=404)

    user_data = user_snapshot.to_dict()
    user_id = user_snapshot.id

    # Get all followed users
    following_docs = firestore_db.collection("User").document(user_id).collection("following").stream()
    following = []
    for doc in following_docs:
        following_id = doc.id
        profile = firestore_db.collection("User").document(following_id).get()
        if profile.exists:
            p_data = profile.to_dict()
            p_data["id"] = profile.id
            following.append(p_data)

    return templates.TemplateResponse("follow_list.html", {"request": request, "title": f"{username}'s Following", "users": following})

async def show_followers(request: Request, username: str, templates: Jinja2Templates):
    user_query = firestore_db.collection('User').where('Username', '==', username).limit(1)
    user_snapshot = next(user_query.stream(), None)

    if not user_snapshot or not user_snapshot.exists:
        return HTMLResponse(f"User not found", status_code=404)

    user_data = user_snapshot.to_dict()
    user_id = user_snapshot.id

    # Get all followers
    follower_docs = firestore_db.collection("User").document(user_id).collection("followers").stream()

    followers = []
    for doc in follower_docs:
        follower_id = doc.id
        profile = firestore_db.collection("User").document(follower_id).get()
        if profile.exists:
            p_data = profile.to_dict()
            p_data["id"] = profile.id
            followers.append(p_data)

    return templates.TemplateResponse("follow_list.html", {"request": request, "title": f"{username}'s Followers", "users": followers})