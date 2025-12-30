import { useEffect } from 'react';
import { useJobStatus } from '../hooks/useJobStatus';
import { useAppStore } from '../store/appStore';
import type { JobStatus } from '../types/job';
import { STATUS_LABELS, isJobComplete, isJobFailed } from '../types/job';
import { Loader2, AlertTriangle, XCircle, CheckCircle2 } from 'lucide-react';

const PROCESSING_STEPS: { status: JobStatus; label: string }[] = [
  { status: 'queued', label: 'Queued' },
  { status: 'transcribing', label: 'Transcribing Audio' },
  { status: 'translating', label: 'Translating Text' },
  { status: 'synthesizing', label: 'Generating Speech' },
  { status: 'processing_video', label: 'Creating Video' },
  { status: 'done', label: 'Complete' },
];

function getStepIndex(status: JobStatus): number {
  const idx = PROCESSING_STEPS.findIndex((s) => s.status === status);
  return idx >= 0 ? idx : 0;
}

export function ProcessingPage() {
  const { jobId, setStep, setError, reset } = useAppStore();
  const { job, isLoading, isError, error } = useJobStatus(jobId);

  // Navigate to result when complete
  useEffect(() => {
    if (job && isJobComplete(job.status)) {
      setStep('result');
    }
  }, [job, setStep]);

  // Handle errors
  useEffect(() => {
    if (job && isJobFailed(job.status)) {
      setError(job.error_message || 'Job processing failed');
    }
  }, [job, setError]);

  const handleCancel = () => {
    reset();
  };

  if (isLoading && !job) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-8 text-center">
          <Loader2 className="h-12 w-12 text-blue-600 animate-spin mx-auto" />
          <p className="mt-4 text-gray-600">Loading job status...</p>
        </div>
      </div>
    );
  }

  if (isError || !job) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-8">
          <div className="text-center">
            <AlertTriangle className="h-16 w-16 text-amber-500 mb-4 mx-auto" />
            <h2 className="text-xl font-semibold text-gray-800 mb-2">
              Error Loading Job
            </h2>
            <p className="text-gray-600 mb-6">
              {error?.message || 'Could not load job status'}
            </p>
            <button
              onClick={handleCancel}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Start Over
            </button>
          </div>
        </div>
      </div>
    );
  }

  const currentStepIndex = getStepIndex(job.status);
  const isFailed = isJobFailed(job.status);

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow-md p-8">
        {isFailed ? (
          // Failed state
          <div className="text-center">
            <XCircle className="h-16 w-16 text-red-500 mb-4 mx-auto" />
            <h2 className="text-xl font-semibold text-gray-800 mb-2">
              Processing Failed
            </h2>
            <p className="text-gray-600 mb-2">{job.error_message}</p>
            <p className="text-sm text-gray-500 mb-6 font-mono">Job ID: {job.id}</p>
            <button
              onClick={handleCancel}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Try Again
            </button>
          </div>
        ) : (
          // Processing state
          <>
            <div className="text-center mb-8">
              <h2 className="text-2xl font-semibold text-gray-800 mb-2">
                Processing Your Video
              </h2>
              <p className="text-gray-600">
                {STATUS_LABELS[job.status] || job.status}
              </p>
            </div>

            {/* Progress Bar */}
            <div className="mb-8">
              <div className="flex justify-between text-sm text-gray-600 mb-2">
                <span>Progress</span>
                <span>{job.progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-blue-500 h-3 rounded-full transition-all duration-500"
                  style={{ width: `${job.progress}%` }}
                />
              </div>
            </div>

            {/* Processing Steps */}
            <div className="space-y-3">
              {PROCESSING_STEPS.map((step, index) => {
                const isComplete = index < currentStepIndex;
                const isCurrent = index === currentStepIndex;

                return (
                  <div
                    key={step.status}
                    className={`flex items-center p-3 rounded-lg ${
                      isCurrent
                        ? 'bg-blue-50 border border-blue-200'
                        : isComplete
                        ? 'bg-green-50'
                        : 'bg-gray-50'
                    }`}
                  >
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center mr-4 transition-colors ${
                        isComplete
                          ? 'bg-green-500 text-white'
                          : isCurrent
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-200 text-gray-400'
                      }`}
                    >
                      {isComplete ? (
                        <CheckCircle2 className="w-5 h-5" />
                      ) : isCurrent ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <span className="text-sm font-medium">{index + 1}</span>
                      )}
                    </div>
                    <span
                      className={`${
                        isCurrent
                          ? 'text-blue-700 font-medium'
                          : isComplete
                          ? 'text-green-700'
                          : 'text-gray-500'
                      }`}
                    >
                      {step.label}
                    </span>
                    {isCurrent && (
                      <div className="ml-auto flex items-center text-blue-400">
                        <span className="text-xs font-medium mr-2">POLLING</span>
                        <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-ping" />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Job Info */}
            <div className="mt-6 pt-4 border-t border-gray-200">
              <p className="text-xs text-gray-500 text-center">
                Job ID: {job.id}
                {job.video_duration_seconds && (
                  <span className="ml-2">
                    | Duration: {job.video_duration_seconds.toFixed(1)}s
                  </span>
                )}
              </p>
            </div>

            {/* Cancel Button */}
            <div className="mt-4 text-center">
              <button
                onClick={handleCancel}
                className="text-sm text-gray-500 hover:text-gray-700 underline"
              >
                Cancel and start over
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
