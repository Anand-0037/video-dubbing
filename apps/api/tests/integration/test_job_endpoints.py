"""Integration tests for job endpoints."""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_s3_service():
    """Mock S3 service for testing."""
    with patch("app.api.v1.endpoints.jobs.get_s3_service") as mock:
        service = MagicMock()
        service.generate_presigned_upload_url.return_value = (
            "https://s3.amazonaws.com/bucket/uploads/test.mp4?signature=abc123",
            "uploads/test-job-id.mp4",
        )
        service.generate_output_download_urls.return_value = {
            "video": "https://s3.amazonaws.com/bucket/outputs/test_dubbed.mp4?sig=xyz",
            "source_subtitle": "https://s3.amazonaws.com/bucket/subtitles/test_source.srt?sig=xyz",
            "target_subtitle": "https://s3.amazonaws.com/bucket/subtitles/test_target.srt?sig=xyz",
        }
        service.get_output_file_sizes.return_value = {
            "video": 45678900,
            "source_subtitle": 2048,
            "target_subtitle": 2156,
        }
        mock.return_value = service
        yield service


class TestCreateJob:
    """Tests for POST /api/v1/jobs endpoint."""

    def test_create_job_success(self, client, mock_s3_service):
        """Test successful job creation."""
        response = client.post(
            "/api/v1/jobs",
            json={
                "filename": "test_video.mp4",
                "content_type": "video/mp4",
                "file_size": 50000000,
                "source_language": "english",
                "target_language": "hindi",
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "job_id" in data["data"]
        assert data["data"]["job_id"].startswith("job_")
        assert "upload_url" in data["data"]
        assert data["data"]["upload_url"].startswith("https://s3.amazonaws.com")
        assert data["data"]["status"] == "created"
        assert data["data"]["expires_in"] == 900
        assert data["error"] is None

    def test_create_job_file_too_large(self, client, mock_s3_service):
        """Test job creation with file size exceeding limit."""
        from app.services.s3_service import S3ValidationError

        mock_s3_service.generate_presigned_upload_url.side_effect = S3ValidationError(
            "File size exceeds maximum allowed size of 100MB"
        )

        response = client.post(
            "/api/v1/jobs",
            json={
                "filename": "large_video.mp4",
                "content_type": "video/mp4",
                "file_size": 150000000,
                "source_language": "english",
                "target_language": "hindi",
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
            },
        )

        # Pydantic validation catches this before S3 service
        assert response.status_code == 422

    def test_create_job_invalid_content_type(self, client, mock_s3_service):
        """Test job creation with invalid content type."""
        response = client.post(
            "/api/v1/jobs",
            json={
                "filename": "test.avi",
                "content_type": "video/avi",
                "file_size": 50000000,
                "source_language": "english",
                "target_language": "hindi",
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
            },
        )

        # Pydantic validation catches this
        assert response.status_code == 422

    def test_create_job_invalid_filename(self, client, mock_s3_service):
        """Test job creation with non-mp4 filename."""
        response = client.post(
            "/api/v1/jobs",
            json={
                "filename": "test.avi",
                "content_type": "video/mp4",
                "file_size": 50000000,
                "source_language": "english",
                "target_language": "hindi",
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
            },
        )

        assert response.status_code == 422

    def test_create_job_unsupported_target_language(self, client, mock_s3_service):
        """Test job creation with unsupported target language."""
        response = client.post(
            "/api/v1/jobs",
            json={
                "filename": "test.mp4",
                "content_type": "video/mp4",
                "file_size": 50000000,
                "source_language": "english",
                "target_language": "spanish",
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
            },
        )

        assert response.status_code == 422


class TestEnqueueJob:
    """Tests for POST /api/v1/jobs/{job_id}/enqueue endpoint."""

    def test_enqueue_job_success(self, client, mock_s3_service):
        """Test successful job enqueue."""
        # First create a job
        create_response = client.post(
            "/api/v1/jobs",
            json={
                "filename": "test_video.mp4",
                "content_type": "video/mp4",
                "file_size": 50000000,
                "source_language": "english",
                "target_language": "hindi",
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
            },
        )
        job_id = create_response.json()["data"]["job_id"]

        # Enqueue the job
        response = client.post(f"/api/v1/jobs/{job_id}/enqueue")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["job_id"] == job_id
        assert data["data"]["status"] == "queued"
        assert "queued for processing" in data["data"]["message"]

    def test_enqueue_nonexistent_job(self, client):
        """Test enqueuing a job that doesn't exist."""
        response = client.post("/api/v1/jobs/nonexistent-job-id/enqueue")

        assert response.status_code == 404


class TestGetJobStatus:
    """Tests for GET /api/v1/jobs/{job_id} endpoint."""

    def test_get_job_status_created(self, client, mock_s3_service):
        """Test getting status of newly created job."""
        # Create a job
        create_response = client.post(
            "/api/v1/jobs",
            json={
                "filename": "test_video.mp4",
                "content_type": "video/mp4",
                "file_size": 50000000,
                "source_language": "english",
                "target_language": "hindi",
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
            },
        )
        job_id = create_response.json()["data"]["job_id"]

        # Get job status
        response = client.get(f"/api/v1/jobs/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["job_id"] == job_id
        assert data["data"]["status"] == "created"
        assert data["data"]["progress"] == 0
        assert data["data"]["source_language"] == "english"
        assert data["data"]["target_language"] == "hindi"
        assert data["data"]["voice_id"] == "21m00Tcm4TlvDq8ikWAM"
        assert data["data"]["error_message"] is None
        assert "created_at" in data["data"]
        assert "updated_at" in data["data"]

    def test_get_job_status_queued(self, client, mock_s3_service):
        """Test getting status of queued job."""
        # Create and enqueue a job
        create_response = client.post(
            "/api/v1/jobs",
            json={
                "filename": "test_video.mp4",
                "content_type": "video/mp4",
                "file_size": 50000000,
                "source_language": "english",
                "target_language": "hindi",
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
            },
        )
        job_id = create_response.json()["data"]["job_id"]
        client.post(f"/api/v1/jobs/{job_id}/enqueue")

        # Get job status
        response = client.get(f"/api/v1/jobs/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "queued"
        assert data["data"]["progress"] == 0

    def test_get_nonexistent_job(self, client):
        """Test getting status of non-existent job."""
        response = client.get("/api/v1/jobs/nonexistent-job-id")

        assert response.status_code == 404


class TestGetDownloadUrls:
    """Tests for GET /api/v1/jobs/{job_id}/download endpoint."""

    def test_get_download_urls_job_not_completed(self, client, mock_s3_service):
        """Test getting download URLs for incomplete job."""
        # Create a job
        create_response = client.post(
            "/api/v1/jobs",
            json={
                "filename": "test_video.mp4",
                "content_type": "video/mp4",
                "file_size": 50000000,
                "source_language": "english",
                "target_language": "hindi",
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
            },
        )
        job_id = create_response.json()["data"]["job_id"]

        # Try to get download URLs
        response = client.get(f"/api/v1/jobs/{job_id}/download")

        assert response.status_code == 400

    def test_get_download_urls_nonexistent_job(self, client):
        """Test getting download URLs for non-existent job."""
        response = client.get("/api/v1/jobs/nonexistent-job-id/download")

        assert response.status_code == 404


class TestDeleteJob:
    """Tests for DELETE /api/v1/jobs/{job_id} endpoint."""

    def test_delete_job_success(self, client, mock_s3_service):
        """Test successful job deletion."""
        # Create a job
        create_response = client.post(
            "/api/v1/jobs",
            json={
                "filename": "test_video.mp4",
                "content_type": "video/mp4",
                "file_size": 50000000,
                "source_language": "english",
                "target_language": "hindi",
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
            },
        )
        job_id = create_response.json()["data"]["job_id"]

        # Delete the job
        response = client.delete(f"/api/v1/jobs/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["job_id"] == job_id
        assert data["data"]["deleted"] is True

        # Verify job is deleted
        get_response = client.get(f"/api/v1/jobs/{job_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_job_idempotent(self, client):
        """Test deleting non-existent job is idempotent."""
        response = client.delete("/api/v1/jobs/nonexistent-job-id")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["deleted"] is False


class TestJobWorkflow:
    """Integration tests for complete job workflow."""

    def test_complete_job_workflow(self, client, mock_s3_service):
        """Test complete job workflow from creation to status check."""
        # Step 1: Create job
        create_response = client.post(
            "/api/v1/jobs",
            json={
                "filename": "test_video.mp4",
                "content_type": "video/mp4",
                "file_size": 50000000,
                "source_language": "english",
                "target_language": "hindi",
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
            },
        )
        assert create_response.status_code == 201
        job_id = create_response.json()["data"]["job_id"]
        upload_url = create_response.json()["data"]["upload_url"]
        assert upload_url.startswith("https://s3.amazonaws.com")

        # Step 2: Check initial status
        status_response = client.get(f"/api/v1/jobs/{job_id}")
        assert status_response.status_code == 200
        assert status_response.json()["data"]["status"] == "created"

        # Step 3: Enqueue job (simulating successful upload)
        enqueue_response = client.post(f"/api/v1/jobs/{job_id}/enqueue")
        assert enqueue_response.status_code == 200
        assert enqueue_response.json()["data"]["status"] == "queued"

        # Step 4: Check queued status
        status_response = client.get(f"/api/v1/jobs/{job_id}")
        assert status_response.status_code == 200
        assert status_response.json()["data"]["status"] == "queued"
        assert status_response.json()["data"]["progress"] == 0

        # Step 5: Try to get download URLs (should fail - not completed)
        download_response = client.get(f"/api/v1/jobs/{job_id}/download")
        assert download_response.status_code == 400

    def test_job_lifecycle_with_deletion(self, client, mock_s3_service):
        """Test job lifecycle including deletion."""
        # Create job
        create_response = client.post(
            "/api/v1/jobs",
            json={
                "filename": "test_video.mp4",
                "content_type": "video/mp4",
                "file_size": 50000000,
                "source_language": "english",
                "target_language": "hindi",
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
            },
        )
        job_id = create_response.json()["data"]["job_id"]

        # Enqueue job
        client.post(f"/api/v1/jobs/{job_id}/enqueue")

        # Delete job
        delete_response = client.delete(f"/api/v1/jobs/{job_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["data"]["deleted"] is True

        # Verify job is gone
        status_response = client.get(f"/api/v1/jobs/{job_id}")
        assert status_response.status_code == 404
