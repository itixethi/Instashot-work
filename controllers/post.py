from fastapi import Request, UploadFile, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from google.auth.transport import requests
from google.cloud import firestore
from starlette import status
from google.cloud import storage
import datetime
import uuid

from firebase.helpers import validateFirebaseToken
from local_constants import PROJECT_STORAGE_BUCKET

firestore_db = firestore.Client()
firebase_request_adapter = requests.Request()

storage_client = storage.Client()
bucket = storage_client.bucket(PROJECT_STORAGE_BUCKET)

async def show_upload_form(request: Request, templates: Jinja2Templates):
    try:
        id_token_cookie = request.cookies.get("token")
        user_token = validateFirebaseToken(id_token=id_token_cookie, firebase_request_adapter=firebase_request_adapter)
        isAuthorized = user_token is not None

        if not isAuthorized:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

        return templates.TemplateResponse(request=request, name="uploadPost.html", context={"isAuthorized": isAuthorized, "request": request})
    except Exception as e:
        return HTMLResponse(str(e), status_code=500)\
    
async def upload_post(request: Request):
    try:
        form = await request.form()
        id_token_cookie = request.cookies.get("token")
        user_token = validateFirebaseToken(id_token=id_token_cookie, firebase_request_adapter=firebase_request_adapter)
        if not user_token:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

        user_id = user_token["user_id"]
        caption = form.get("caption")
        file: UploadFile = form.get("file")

        if not file:
            return RedirectResponse(url="/upload-post?error=No+file+uploaded", status_code=status.HTTP_400_BAD_REQUEST)

        # Fetch Username (handle) from Firestore
        user_doc = firestore_db.collection("User").document(user_id).get()
        username = "Unknown"
        if user_doc.exists:
            user_data = user_doc.to_dict()
            username = user_data.get("Username", "Unknown")

        # Save file to Google Cloud Storage
        file_extension = file.filename.split(".")[-1]
        blob_name = f"posts/{uuid.uuid4()}.{file_extension}"
        blob = bucket.blob(blob_name)
        blob.upload_from_file(file.file, content_type=file.content_type)
        blob.make_public()

        # Generate public URL
        image_url = blob.public_url

        # Save Post to Firestore
        firestore_db.collection("Post").add({"Username": username, "UserID": user_id, "Caption": caption, "ImageURL": image_url, "Date": datetime.datetime.utcnow()})

        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        return HTMLResponse(str(e), status_code=500)
    
async def upload_profile_image(request: Request, file: UploadFile):
    try:
        id_token = request.cookies.get("token")
        user_token = validateFirebaseToken(id_token=id_token, firebase_request_adapter=firebase_request_adapter)
        if not user_token:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

        user_id = user_token["user_id"]

        # Upload image to GCS
        extension = file.filename.split('.')[-1]
        blob_name = f"profile_images/{uuid.uuid4()}.{extension}"
        blob = bucket.blob(blob_name)
        blob.upload_from_file(file.file, content_type=file.content_type)
        blob.make_public()

        image_url = f"https://storage.googleapis.com/{bucket.name}/{blob_name}"

        # Update Firestore user document
        firestore_db.collection("User").document(user_id).update({
            "ProfileImageURL": image_url
        })

        return RedirectResponse(url=f"/profile/{user_token.get('name')}", status_code=status.HTTP_303_SEE_OTHER)
    
    except Exception as e:
        return HTMLResponse(str(e), status_code=500)