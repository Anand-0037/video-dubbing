"""Test S3 service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from app.services.s3_service import S3Service, S3ValidationError


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    with patch("dubwizard_shared.services.s3_service.boto3.client") as mock_client:
        yield mock_client.return_value


@pytest.fixture
def s3_service(mock_s3_client):
    """Create S3Service instance with mocked client."""
    service = S3Service()
    # Force use of boto3 client for tests
    service.is_dev = False
    service.s3_client = mock_s3_client
    return service


@pytest.mark.unit
def test_generate_presigned_upload_url(s3_service, mock_s3_client):
    """Test generating presigned upload URL."""
    mock_s3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/bucket/uploads/test.mp4?signature=xyz"

    url, s3_key = s3_service.generate_presigned_upload_url(
        filename="test.mp4",
        content_type="video/mp4",
        expires_in=900
    )

    assert url.startswith("https://s3.amazonaws.com")
    assert s3_key.startswith("uploads/")
    assert s3_key.endswith(".mp4")

    # Verify boto3 was called correctly
    mock_s3_client.generate_presigned_url.assert_called_once()
    call_args = mock_s3_client.generate_presigned_url.call_args
    assert call_args[0][0] == "put_object"
    assert call_args[1]["Params"]["ContentType"] == "video/mp4"
    assert call_args[1]["ExpiresIn"] == 900


@pytest.mark.unit
def test_generate_presigned_upload_url_with_custom_extension(s3_service, mock_s3_client):
    """Test generating presigned upload URL with custom file extension."""
    mock_s3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/bucket/uploads/test.mp4"

    url, s3_key = s3_service.generate_presigned_upload_url(
        filename="my-video.mp4",
        content_type="video/mp4"
    )

    assert s3_key.endswith(".mp4")


@pytest.mark.unit
def test_generate_presigned_download_url(s3_service, mock_s3_client):
    """Test generating presigned download URL."""
    mock_s3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/bucket/outputs/test.mp4?signature=xyz"

    url = s3_service.generate_presigned_download_url(
        s3_key="outputs/test.mp4",
        expires_in=3600
    )

    assert url.startswith("https://s3.amazonaws.com")

    # Verify boto3 was called correctly
    mock_s3_client.generate_presigned_url.assert_called_once()
    call_args = mock_s3_client.generate_presigned_url.call_args
    assert call_args[0][0] == "get_object"
    assert call_args[1]["Params"]["Key"] == "outputs/test.mp4"
    assert call_args[1]["ExpiresIn"] == 3600


@pytest.mark.unit
def test_generate_presigned_download_url_with_filename(s3_service, mock_s3_client):
    """Test generating presigned download URL with custom filename."""
    mock_s3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/bucket/outputs/test.mp4"

    url = s3_service.generate_presigned_download_url(
        s3_key="outputs/test.mp4",
        filename="my-dubbed-video.mp4"
    )

    # Verify Content-Disposition header was set
    call_args = mock_s3_client.generate_presigned_url.call_args
    assert "ResponseContentDisposition" in call_args[1]["Params"]
    assert "my-dubbed-video.mp4" in call_args[1]["Params"]["ResponseContentDisposition"]


@pytest.mark.unit
def test_file_exists_true(s3_service, mock_s3_client):
    """Test checking if file exists (file exists)."""
    mock_s3_client.head_object.return_value = {"ContentLength": 1024}

    exists = s3_service.file_exists("uploads/test.mp4")

    assert exists is True
    mock_s3_client.head_object.assert_called_once_with(
        Bucket=s3_service.bucket_name,
        Key="uploads/test.mp4"
    )


@pytest.mark.unit
def test_file_exists_false(s3_service, mock_s3_client):
    """Test checking if file exists (file doesn't exist)."""
    error_response = {"Error": {"Code": "404"}}
    mock_s3_client.head_object.side_effect = ClientError(error_response, "head_object")

    exists = s3_service.file_exists("uploads/nonexistent.mp4")

    assert exists is False


@pytest.mark.unit
def test_get_file_size(s3_service, mock_s3_client):
    """Test getting file size."""
    mock_s3_client.head_object.return_value = {"ContentLength": 52428800}

    size = s3_service.get_file_size("uploads/test.mp4")

    assert size == 52428800
    mock_s3_client.head_object.assert_called_once()


@pytest.mark.unit
def test_get_file_size_not_found(s3_service, mock_s3_client):
    """Test getting file size for non-existent file."""
    error_response = {"Error": {"Code": "404"}}
    mock_s3_client.head_object.side_effect = ClientError(error_response, "head_object")

    with pytest.raises(ClientError):
        s3_service.get_file_size("uploads/nonexistent.mp4")


@pytest.mark.unit
def test_upload_file(s3_service, mock_s3_client):
    """Test uploading file to S3."""
    mock_s3_client.upload_file.return_value = None

    s3_key = s3_service.upload_file("/tmp/test.mp4", "outputs/test.mp4")

    assert s3_key == "outputs/test.mp4"
    mock_s3_client.upload_file.assert_called_once_with(
        "/tmp/test.mp4",
        s3_service.bucket_name,
        "outputs/test.mp4"
    )


@pytest.mark.unit
def test_download_file(s3_service, mock_s3_client):
    """Test downloading file from S3."""
    mock_s3_client.download_file.return_value = None

    local_path = s3_service.download_file("uploads/test.mp4", "/tmp/test.mp4")

    assert local_path == "/tmp/test.mp4"
    mock_s3_client.download_file.assert_called_once_with(
        s3_service.bucket_name,
        "uploads/test.mp4",
        "/tmp/test.mp4"
    )


@pytest.mark.unit
def test_delete_file(s3_service, mock_s3_client):
    """Test deleting file from S3."""
    mock_s3_client.delete_object.return_value = None

    s3_service.delete_file("uploads/test.mp4")

    mock_s3_client.delete_object.assert_called_once_with(
        Bucket=s3_service.bucket_name,
        Key="uploads/test.mp4"
    )


@pytest.mark.unit
def test_generate_presigned_upload_url_error(s3_service, mock_s3_client):
    """Test error handling when generating presigned upload URL."""
    error_response = {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}
    mock_s3_client.generate_presigned_url.side_effect = ClientError(error_response, "generate_presigned_url")

    with pytest.raises(ClientError):
        s3_service.generate_presigned_upload_url("test.mp4")


@pytest.mark.unit
def test_s3_key_uniqueness(s3_service, mock_s3_client):
    """Test that generated S3 keys are unique."""
    mock_s3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/bucket/test"

    _, key1 = s3_service.generate_presigned_upload_url("test.mp4")
    _, key2 = s3_service.generate_presigned_upload_url("test.mp4")

    assert key1 != key2
    assert key1.startswith("uploads/")
    assert key2.startswith("uploads/")


@pytest.mark.unit
def test_generate_presigned_upload_url_with_file_size(s3_service, mock_s3_client):
    """Test generating presigned upload URL with file size validation."""
    mock_s3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/bucket/uploads/test.mp4"

    url, s3_key = s3_service.generate_presigned_upload_url(
        filename="test.mp4",
        content_type="video/mp4",
        file_size=50 * 1024 * 1024,  # 50MB
        expires_in=900
    )

    # Verify ContentLength was included
    call_args = mock_s3_client.generate_presigned_url.call_args
    assert call_args[1]["Params"]["ContentLength"] == 50 * 1024 * 1024


@pytest.mark.unit
def test_generate_presigned_upload_url_file_too_large(s3_service, mock_s3_client):
    """Test validation error for file too large."""
    with pytest.raises(S3ValidationError, match="exceeds maximum"):
        s3_service.generate_presigned_upload_url(
            filename="test.mp4",
            content_type="video/mp4",
            file_size=200 * 1024 * 1024  # 200MB (exceeds 100MB limit)
        )


@pytest.mark.unit
def test_generate_presigned_upload_url_invalid_content_type(s3_service, mock_s3_client):
    """Test validation error for invalid content type."""
    with pytest.raises(S3ValidationError, match="Content type must be video/mp4"):
        s3_service.generate_presigned_upload_url(
            filename="test.mp4",
            content_type="video/avi",
            file_size=50 * 1024 * 1024
        )


@pytest.mark.unit
def test_generate_presigned_upload_url_invalid_filename(s3_service, mock_s3_client):
    """Test validation error for invalid filename."""
    with pytest.raises(S3ValidationError, match="must end with .mp4"):
        s3_service.generate_presigned_upload_url(
            filename="test.avi",
            content_type="video/mp4",
            file_size=50 * 1024 * 1024
        )


@pytest.mark.unit
def test_upload_file_with_retry_success(s3_service, mock_s3_client):
    """Test successful upload with retry."""
    mock_s3_client.upload_file.return_value = None

    s3_key = s3_service.upload_file_with_retry("/tmp/test.mp4", "outputs/test.mp4")

    assert s3_key == "outputs/test.mp4"
    mock_s3_client.upload_file.assert_called_once()


@pytest.mark.unit
def test_upload_file_with_retry_failure_then_success(s3_service, mock_s3_client):
    """Test upload retry logic - fail once then succeed."""
    error_response = {"Error": {"Code": "ServiceUnavailable", "Message": "Service Unavailable"}}
    mock_s3_client.upload_file.side_effect = [
        ClientError(error_response, "upload_file"),  # First attempt fails
        None  # Second attempt succeeds
    ]

    with patch('time.sleep') as mock_sleep:  # Mock sleep to speed up test
        s3_key = s3_service.upload_file_with_retry("/tmp/test.mp4", "outputs/test.mp4", max_retries=2)

    assert s3_key == "outputs/test.mp4"
    assert mock_s3_client.upload_file.call_count == 2
    mock_sleep.assert_called_once_with(1)  # First retry waits 1 second


@pytest.mark.unit
def test_upload_file_with_retry_max_retries_exceeded(s3_service, mock_s3_client):
    """Test upload retry logic - all attempts fail."""
    error_response = {"Error": {"Code": "ServiceUnavailable", "Message": "Service Unavailable"}}
    mock_s3_client.upload_file.side_effect = ClientError(error_response, "upload_file")

    with patch('time.sleep'):  # Mock sleep to speed up test
        with pytest.raises(ClientError):
            s3_service.upload_file_with_retry("/tmp/test.mp4", "outputs/test.mp4", max_retries=2)

    assert mock_s3_client.upload_file.call_count == 3  # Initial + 2 retries


@pytest.mark.unit
def test_download_file_with_retry_success(s3_service, mock_s3_client):
    """Test successful download with retry."""
    mock_s3_client.download_file.return_value = None

    local_path = s3_service.download_file_with_retry("uploads/test.mp4", "/tmp/test.mp4")

    assert local_path == "/tmp/test.mp4"
    mock_s3_client.download_file.assert_called_once()


@pytest.mark.unit
def test_generate_output_download_urls(s3_service, mock_s3_client):
    """Test generating all output download URLs for a job."""
    mock_s3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/bucket/test"

    urls = s3_service.generate_output_download_urls("job_123")

    assert "video" in urls
    assert "source_subtitle" in urls
    assert "target_subtitle" in urls
    assert mock_s3_client.generate_presigned_url.call_count == 3


@pytest.mark.unit
def test_get_output_file_sizes(s3_service, mock_s3_client):
    """Test getting file sizes for all output files."""
    mock_s3_client.head_object.side_effect = [
        {"ContentLength": 50000000},  # Video file
        {"ContentLength": 2048},      # Source subtitle
        {"ContentLength": 2156},      # Target subtitle
    ]

    sizes = s3_service.get_output_file_sizes("job_123")

    assert sizes["video"] == 50000000
    assert sizes["source_subtitle"] == 2048
    assert sizes["target_subtitle"] == 2156
    assert mock_s3_client.head_object.call_count == 3
