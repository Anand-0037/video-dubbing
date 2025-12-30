/**
 * Job-related TypeScript types matching backend schemas.
 */

export type JobStatus =
  | 'created'
  | 'uploading'
  | 'queued'
  | 'processing'
  | 'transcribing'
  | 'translating'
  | 'synthesizing'
  | 'processing_video'
  | 'done'
  | 'failed';

export interface Job {
  id: string;
  status: JobStatus;
  progress: number;
  input_s3_key: string;
  source_language: string;
  target_language: string;
  voice_id: string;
  output_video_s3_key?: string;
  source_subtitle_s3_key?: string;
  target_subtitle_s3_key?: string;
  video_duration_seconds?: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface CreateJobRequest {
  filename: string;
  file_size: number;
  content_type: string;
  target_language: string;
  voice_id: string;
  source_language?: string;
}

export interface CreateJobResponse {
  job_id: string;
  status: JobStatus;
  upload_url: string;
  s3_key: string;
}

export interface DownloadFile {
  url: string;
  filename: string;
  size_bytes: number;
  expires_in: number;
}

export interface SubtitleFiles {
  source: DownloadFile;
  target: DownloadFile;
}

export interface DownloadResponse {
  video: DownloadFile;
  subtitles: SubtitleFiles;
}

export interface VoiceOption {
  id: string;
  name: string;
  description: string;
  gender: 'male' | 'female';
}

// Predefined voice options for MVP (ElevenLabs voices)
export const VOICE_OPTIONS: VoiceOption[] = [
  {
    id: 'pNInz6obpgDQGcFmaJgB',
    name: 'Adam',
    description: 'Deep, warm male voice',
    gender: 'male',
  },
  {
    id: 'EXAVITQu4vr4xnSDxMaL',
    name: 'Bella',
    description: 'Soft, expressive female voice',
    gender: 'female',
  },
];

// Status display helpers
export const STATUS_LABELS: Record<JobStatus, string> = {
  created: 'Created',
  uploading: 'Uploading',
  queued: 'Queued',
  processing: 'Processing',
  transcribing: 'Transcribing Audio',
  translating: 'Translating',
  synthesizing: 'Generating Speech',
  processing_video: 'Processing Video',
  done: 'Complete',
  failed: 'Failed',
};

export const isJobComplete = (status: JobStatus): boolean => status === 'done';
export const isJobFailed = (status: JobStatus): boolean => status === 'failed';
export const isJobProcessing = (status: JobStatus): boolean =>
  !isJobComplete(status) && !isJobFailed(status);
