import { useRef, useState } from 'react';
import { formatApiError } from '../services/api';
import { jobService } from '../services/jobService';
import { useAppStore } from '../store/appStore';
import type { VoiceOption } from '../types/job';
import { VOICE_OPTIONS } from '../types/job';
import { Video, FileVideo, Upload, Mic, User, Languages, CheckCircle, AlertCircle } from 'lucide-react';

const MAX_FILE_SIZE_MB = Number(import.meta.env.VITE_MAX_FILE_SIZE_MB) || 100;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

export function UploadPage() {
  const { setStep, setJobId, setUploadProgress, setError } = useAppStore();

  const [file, setFile] = useState<File | null>(null);
  const [voiceId, setVoiceId] = useState<string>(VOICE_OPTIONS[0].id);
  const [isUploading, setIsUploading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [uploadPercent, setUploadPercent] = useState(0);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    setLocalError(null);

    if (!selectedFile) return;

    // Validate file type
    if (!selectedFile.type.includes('video/mp4') && !selectedFile.name.endsWith('.mp4')) {
      setLocalError('Please select an MP4 video file');
      return;
    }

    // Validate file size
    if (selectedFile.size > MAX_FILE_SIZE_BYTES) {
      setLocalError(`File size must be less than ${MAX_FILE_SIZE_MB}MB`);
      return;
    }

    setFile(selectedFile);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      const fakeEvent = {
        target: { files: [droppedFile] },
      } as unknown as React.ChangeEvent<HTMLInputElement>;
      handleFileSelect(fakeEvent);
    }
  };

  const handleSubmit = async () => {
    if (!file) return;

    setIsUploading(true);
    setLocalError(null);
    setUploadPercent(0);

    try {
      // Step 1: Create job and get presigned URL
      const createResponse = await jobService.createJob({
        filename: file.name,
        file_size: file.size,
        content_type: 'video/mp4',
        target_language: 'hindi',
        voice_id: voiceId,
        source_language: 'english',
      });

      setJobId(createResponse.job_id);

      // Step 2: Upload to S3
      await jobService.uploadToS3(createResponse.upload_url, file, (progress) => {
        setUploadPercent(progress);
        setUploadProgress(progress);
      });

      // Step 3: Enqueue job for processing
      await jobService.enqueueJob(createResponse.job_id);

      // Move to processing step
      setStep('processing');
    } catch (err) {
      const errorMessage = formatApiError(err);
      setLocalError(errorMessage);
      setError(errorMessage);
    } finally {
      setIsUploading(false);
    }
  };

  const selectedVoice = VOICE_OPTIONS.find((v) => v.id === voiceId);

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-semibold text-gray-800 mb-6">
          Upload Your Video
        </h2>

        {/* File Drop Zone */}
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            file
              ? 'border-green-400 bg-green-50'
              : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50'
          }`}
          onClick={() => fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="video/mp4,.mp4"
            onChange={handleFileSelect}
            className="hidden"
          />

          {file ? (
            <div className="flex flex-col items-center">
              <FileVideo className="w-16 h-16 text-green-500 mb-2" />
              <div className="text-green-600 text-lg font-medium">{file.name}</div>
              <div className="text-gray-500 text-sm mt-1">
                {(file.size / (1024 * 1024)).toFixed(2)} MB
              </div>
              <div className="text-blue-500 text-sm mt-2 flex items-center justify-center">
                <Upload className="w-4 h-4 mr-1" />
                Click to change file
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <div className="text-gray-300 mb-4">
                <Video className="w-16 h-16" />
              </div>
              <div className="text-gray-600 font-medium">
                Drag and drop your MP4 video here, or click to browse
              </div>
              <div className="text-gray-400 text-sm mt-2">
                Max file size: {MAX_FILE_SIZE_MB}MB | Max duration: 60 seconds
              </div>
            </div>
          )}
        </div>

        {/* Configuration */}
        <div className="mt-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center">
              <Languages className="w-4 h-4 mr-2 text-gray-400" />
              Target Language
            </label>
            <div className="bg-gray-100 rounded-md px-4 py-2 text-gray-700 font-medium">
              Hindi (हिन्दी)
            </div>
            <p className="text-xs text-gray-500 mt-1">
              More languages coming soon
            </p>
          </div>

          {/* Voice Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center">
              <Mic className="w-4 h-4 mr-2 text-gray-400" />
              Voice Style
            </label>
            <div className="grid grid-cols-2 gap-3">
              {VOICE_OPTIONS.map((voice: VoiceOption) => (
                <button
                  key={voice.id}
                  type="button"
                  onClick={() => setVoiceId(voice.id)}
                  className={`p-3 rounded-lg border-2 text-left transition-all ${
                    voiceId === voice.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex justify-between items-start mb-1">
                    <div className="font-semibold text-gray-800">{voice.name}</div>
                    {voiceId === voice.id && <CheckCircle className="w-4 h-4 text-blue-500" />}
                  </div>
                  <div className="text-xs text-gray-500 mb-2">{voice.description}</div>
                  <div className="flex items-center text-xs text-gray-400 capitalize">
                    <User className="w-3 h-3 mr-1" />
                    {voice.gender}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Error Message */}
        {localError && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm flex items-start">
            <AlertCircle className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
            <div>{localError}</div>
          </div>
        )}

        {/* Upload Progress */}
        {isUploading && (
          <div className="mt-4">
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>Uploading...</span>
              <span>{uploadPercent}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${uploadPercent}%` }}
              />
            </div>
          </div>
        )}

        {/* Submit Button */}
        <button
          onClick={handleSubmit}
          disabled={!file || isUploading}
          className={`mt-6 w-full py-3 px-4 rounded-lg font-medium text-white transition-colors ${
            !file || isUploading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {isUploading ? 'Processing...' : 'Start Dubbing'}
        </button>

        {/* Info */}
        <p className="mt-4 text-xs text-gray-500 text-center">
          Your video will be dubbed from English to {selectedVoice?.name}'s voice in Hindi
        </p>
      </div>
    </div>
  );
}
