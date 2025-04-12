# Flask Photo Gallery

A lightweight, cloud-native photo gallery application built with Python Flask and Azure Blob Storage. This application provides a simple yet powerful way to store, manage, and display your photo collection with efficient thumbnail generation for optimal performance.

## Features

- **Cloud Storage**: Leverages Azure Blob Storage (with local Azurite emulation for development)
- **Thumbnail Generation**: Automatically creates optimized thumbnails for faster gallery browsing
- **Responsive Design**: Mobile-friendly interface that works across all devices
- **Easy Deployment**: Designed for simple deployment to Azure App Service
- **Developer Friendly**: Well-documented code with Google-style docstrings

Perfect for personal photo collections, portfolios, or small business galleries without the overhead of a complex content management system. Ideal for developers looking for a lightweight starting point to build upon.

## Prerequisites

- Python 3.9 or higher
- Pip package manager
- Azurite storage emulator (for local development)
- Azure account (for production deployment)

## Required Packages

```bash
pip install flask azure-storage-blob python-dotenv pillow
```

## Environment Variables

| Variable | Description | Default (Development) |
|----------|-------------|----------------------|
| `FLASK_APP` | Entry point for Flask application | app.py |
| `FLASK_ENV` | Environment setting for Flask | development |
| `SECRET_KEY` | Secret key for session security | *must be set* |
| `AZURITE_URL` | URL for Azurite/Azure Blob Storage | http://127.0.0.1:10000/devstoreaccount1 |
| `AZURITE_KEY` | Access key for Azurite/Azure Storage | *default Azurite key* |
| `CONTAINER_NAME` | Container name for full-size images | gallery-images |
| `THUMBNAIL_CONTAINER_NAME` | Container name for thumbnails | gallery-thumbnails |

For production deployment, you'll also need to set:

- `AZURE_STORAGE_CONNECTION_STRING` or
- `AZURE_STORAGE_ACCOUNT_NAME` and `AZURE_STORAGE_ACCOUNT_KEY`

## Setup Instructions

1. Clone this repository
2. Copy the `.env.template` file to `.env` and update as needed
3. Start Azurite for local storage emulation
4. Run `flask run` to start the development server