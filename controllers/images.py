import uuid
from google.cloud import storage
import local_constants

def get_storage_client_and_bucket():
    """Initialize and return the GCS client and target bucket."""
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    return storage_client, bucket

def upload_image(file):
    """
    Upload an image to the GCS bucket and return its public URL.
    Automatically generates a unique name.
    """
    _, bucket = get_storage_client_and_bucket()

    # Generate a unique blob name
    extension = file.filename.split('.')[-1]
    blob_name = f"posts/{uuid.uuid4()}.{extension}"

    blob = bucket.blob(blob_name)
    blob.upload_from_file(file.file, content_type=file.content_type)
    blob.make_public()

    return blob.public_url

def list_public_images(prefix="posts/"):
    """
    List all public image URLs under a given prefix.
    """
    storage_client, _ = get_storage_client_and_bucket()
    blobs = storage_client.list_blobs(local_constants.PROJECT_STORAGE_BUCKET, prefix=prefix)
    return [blob.public_url for blob in blobs]

def download_image_bytes(filename):
    """
    Download image data as bytes from GCS.
    Useful for previewing or forwarding images.
    """
    storage_client, bucket = get_storage_client_and_bucket()
    blob = bucket.get_blob(filename)
    if blob:
        return blob.download_as_bytes()
    return None