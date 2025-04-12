"""Flask application to upload and display images in a gallery."""

from flask import Flask, render_template, request, redirect, url_for, send_file
import os
from werkzeug.utils import secure_filename
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import uuid
from io import BytesIO
from dotenv import load_dotenv
from PIL import Image
import io

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-key')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Azurite connection settings from environment variables with defaults for local dev
AZURITE_URL = os.environ.get('AZURITE_URL', 'http://127.0.0.1:10000/devstoreaccount1')
AZURITE_KEY = os.environ.get('AZURITE_KEY',
                             'Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==')
CONTAINER_NAME = os.environ.get('CONTAINER_NAME', 'gallery-images')
THUMBNAIL_CONTAINER_NAME = os.environ.get('THUMBNAIL_CONTAINER_NAME', 'gallery-thumbnails')
THUMBNAIL_SIZE = (300, 300)  # Width, Height in pixels


def get_blob_service_client():
    """
    Creates a BlobServiceClient for interacting with Azure Blob Storage or Azurite emulator.

    Uses the account URL and credential from environment variables to create
    a client that can perform operations on blob storage containers and blobs.

    Returns:
        BlobServiceClient: Client for interacting with the blob storage service.
    """
    return BlobServiceClient(
        account_url=AZURITE_URL,
        credential=AZURITE_KEY
    )


def get_container_client(container_name=CONTAINER_NAME):
    """
    Creates a ContainerClient for the specified container.

    Args:
        container_name (str): Name of the container to get client for.
            Defaults to the main images container.

    Returns:
        ContainerClient: Client for interacting with a specific blob container.
    """
    blob_service_client = get_blob_service_client()
    return blob_service_client.get_container_client(container_name)


def allowed_file(filename):
    """
    Checks if the provided filename has an allowed extension.

    Args:
        filename (str): The filename to check.

    Returns:
        bool: True if the file extension is allowed, False otherwise.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def ensure_container_exists(container_name=CONTAINER_NAME):
    """
    Creates the container if it doesn't exist.

    Args:
        container_name (str): Name of the container to check/create.
            Defaults to the main images container.

    Raises:
        Exception: If creating the container fails.
    """
    blob_service_client = get_blob_service_client()
    try:
        container_client = blob_service_client.get_container_client(container_name)
        # Check if container exists by accessing its properties
        container_client.get_container_properties()
    except Exception:
        # Container doesn't exist, create it with public access
        blob_service_client.create_container(container_name, public_access="blob")


def create_thumbnail(image_data):
    """
    Creates a thumbnail of the provided image data.

    Args:
        image_data (bytes): The original image data as bytes.

    Returns:
        bytes: The thumbnail image data as bytes.

    Raises:
        Exception: If thumbnail generation fails.
    """
    try:
        # Open the image using PIL
        image = Image.open(BytesIO(image_data))

        # Convert to RGB if mode is RGBA (for PNG support)
        if image.mode == 'RGBA':
            image = image.convert('RGB')

        # Create thumbnail (maintains aspect ratio)
        image.thumbnail(THUMBNAIL_SIZE)

        # Save to bytes
        thumbnail_bytes = BytesIO()
        image.save(thumbnail_bytes, format='JPEG', quality=85, optimize=True)
        thumbnail_bytes.seek(0)

        return thumbnail_bytes.read()
    except Exception as e:
        app.logger.error(f"Error creating thumbnail: {str(e)}")
        raise


def get_thumbnail_name(original_name):
    """
    Generates a thumbnail filename based on the original filename.

    Args:
        original_name (str): The original filename.

    Returns:
        str: The thumbnail filename.
    """
    return f"thumb_{original_name}"


@app.route('/')
def gallery():
    """
    Renders the gallery page with all images from blob storage.

    Ensures the container exists, retrieves all blob names from the container,
    and passes them to the gallery template for rendering.

    Returns:
        str: Rendered HTML for the gallery page.
    """
    # Ensure containers exist
    ensure_container_exists(CONTAINER_NAME)
    ensure_container_exists(THUMBNAIL_CONTAINER_NAME)

    # Get list of blobs in container
    container_client = get_container_client(CONTAINER_NAME)
    blob_list = container_client.list_blobs()

    # Convert to list and extract names
    images = [blob.name for blob in blob_list]

    return render_template('gallery.html', images=images)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """
    Handles the image upload form and file upload process.

    On GET requests, displays the upload form.
    On POST requests, validates the uploaded file, generates a thumbnail,
    and stores both the original and thumbnail in blob storage.

    Returns:
        str: On GET, the rendered upload form.
             On successful POST, redirects to the gallery page.
             On failed POST, redirects back to the upload form.
    """
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            return redirect(request.url)

        if file and allowed_file(file.filename):
            # Ensure containers exist
            ensure_container_exists(CONTAINER_NAME)
            ensure_container_exists(THUMBNAIL_CONTAINER_NAME)

            # Create a unique filename to avoid conflicts
            original_filename = secure_filename(file.filename)
            filename = f"{uuid.uuid4()}-{original_filename}"

            # Read file content
            file_contents = file.read()

            # Generate thumbnail
            thumbnail_data = create_thumbnail(file_contents)
            thumbnail_name = get_thumbnail_name(filename)

            # Upload original to main container
            container_client = get_container_client(CONTAINER_NAME)
            blob_client = container_client.get_blob_client(filename)
            blob_client.upload_blob(file_contents)

            # Upload thumbnail to thumbnail container
            thumbnail_container_client = get_container_client(THUMBNAIL_CONTAINER_NAME)
            thumbnail_blob_client = thumbnail_container_client.get_blob_client(thumbnail_name)
            thumbnail_blob_client.upload_blob(thumbnail_data)

            return redirect(url_for('gallery'))

    return render_template('upload.html')


@app.route('/image/<filename>')
def get_image(filename):
    """
    Streams an image directly from blob storage.

    Retrieves the specified blob from storage and sends it as a file response.

    Args:
        filename (str): The name of the blob to retrieve.

    Returns:
        Response: A Flask response object containing the image data.
                 If the blob doesn't exist, returns a 404 error.
    """
    try:
        blob_client = get_blob_service_client().get_blob_client(
            container=CONTAINER_NAME, blob=filename
        )

        # Download the blob
        download_stream = blob_client.download_blob()
        blob_data = download_stream.readall()

        # Determine MIME type from filename
        extension = filename.split(".")[-1].lower()
        mime_type = f'image/{extension}'
        if extension == 'jpg':
            mime_type = 'image/jpeg'

        # Create a BytesIO object and send as file
        return send_file(
            BytesIO(blob_data),
            mimetype=mime_type,
            as_attachment=False,
            download_name=filename
        )
    except Exception as e:
        return str(e), 404


@app.route('/thumbnail/<filename>')
def get_thumbnail(filename):
    """
    Streams a thumbnail image directly from blob storage.

    Retrieves the specified thumbnail blob from storage and sends it as a file response.

    Args:
        filename (str): The name of the original image blob (not the thumbnail).

    Returns:
        Response: A Flask response object containing the thumbnail image data.
                 If the thumbnail doesn't exist, returns a 404 error.
    """
    try:
        # Convert to thumbnail name
        thumbnail_name = get_thumbnail_name(filename)

        blob_client = get_blob_service_client().get_blob_client(
            container=THUMBNAIL_CONTAINER_NAME, blob=thumbnail_name
        )

        # Download the blob
        download_stream = blob_client.download_blob()
        blob_data = download_stream.readall()

        # Create a BytesIO object and send as file
        return send_file(BytesIO(blob_data), mimetype='image/jpeg', download_name=thumbnail_name)
    except Exception as e:
        return str(e), 404


if __name__ == '__main__':
    app.run()
