/**
 * Job service for interacting with the jobs API.
 */

import axios from 'axios';
import type {
    CreateJobRequest,
    CreateJobResponse,
    DownloadResponse,
    Job,
} from '../types/job';
import { apiClient, unwrapResponse } from './api';

export const jobService = {
  /**
   * Create a new dubbing job and get presigned upload URL.
   */
  async createJob(request: CreateJobRequest): Promise<CreateJobResponse> {
    const response = await apiClient.post<CreateJobResponse>('/jobs', request);
    return unwrapResponse(response);
  },

  /**
   * Upload file directly to S3 using presigned URL.
   */
  async uploadToS3(
    presignedUrl: string,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<void> {
    await axios.put(presignedUrl, file, {
      headers: {
        'Content-Type': file.type,
        'Content-Length': file.size.toString(),
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
  },

  /**
   * Enqueue a job for processing after upload is complete.
   */
  async enqueueJob(jobId: string): Promise<Job> {
    const response = await apiClient.post<Job>(`/jobs/${jobId}/enqueue`);
    return unwrapResponse(response);
  },

  /**
   * Get job status and details.
   */
  async getJob(jobId: string): Promise<Job> {
    const response = await apiClient.get<Job>(`/jobs/${jobId}`);
    return unwrapResponse(response);
  },

  /**
   * Get download URLs for completed job.
   */
  async getDownloadUrls(jobId: string): Promise<DownloadResponse> {
    const response = await apiClient.get<DownloadResponse>(`/jobs/${jobId}/download`);
    return unwrapResponse(response);
  },

  /**
   * Delete a job.
   */
  async deleteJob(jobId: string): Promise<void> {
    await apiClient.delete(`/jobs/${jobId}`);
  },
};
