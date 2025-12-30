import { useEffect, useState } from 'react';
import { formatApiError } from '../services/api';
import { jobService } from '../services/jobService';
import { useAppStore } from '../store/appStore';
import type { DownloadResponse } from '../types/job';
import { CheckCircle2, Download, Video, FileText, AlertTriangle, Loader2, ArrowLeft } from 'lucide-react';

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function ResultPage() {
  const { jobId, reset } = useAppStore();
  const [downloadData, setDownloadData] = useState<DownloadResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const fetchDownloadUrls = async () => {
      try {
        const data = await jobService.getDownloadUrls(jobId);
        setDownloadData(data);
      } catch (err) {
        setError(formatApiError(err));
      } finally {
        setIsLoading(false);
      }
    };

    fetchDownloadUrls();
  }, [jobId]);

  const handleStartNew = () => {
    reset();
  };

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-8 text-center">
          <Loader2 className="h-12 w-12 text-blue-600 animate-spin mx-auto" />
          <p className="mt-4 text-gray-600">Preparing download links...</p>
        </div>
      </div>
    );
  }

  if (error || !downloadData) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-8">
          <div className="text-center">
            <AlertTriangle className="h-16 w-16 text-amber-500 mb-4 mx-auto" />
            <h2 className="text-xl font-semibold text-gray-800 mb-2">
              Error Loading Downloads
            </h2>
            <p className="text-gray-600 mb-6">{error || 'Could not load download links'}</p>
            <button
              onClick={handleStartNew}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center justify-center mx-auto"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Start Over
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow-md p-8">
        {/* Success Header */}
        <div className="text-center mb-10">
          <CheckCircle2 className="h-20 w-20 text-green-500 mb-4 mx-auto" />
          <h2 className="text-3xl font-bold text-gray-900 mb-2">
            Your Video is Ready!
          </h2>
          <p className="text-lg text-gray-600">
            Download your dubbed video and subtitles below
          </p>
        </div>

        {/* Download Options */}
        <div className="space-y-4">
          {/* Dubbed Video */}
          <a
            href={downloadData.video.url}
            download={downloadData.video.filename}
            className="flex items-center justify-between p-5 bg-blue-50 rounded-xl border border-blue-200 hover:bg-blue-100 transition-all group"
          >
            <div className="flex items-center">
              <div className="bg-blue-600 p-3 rounded-lg text-white mr-4 shadow-sm">
                <Video className="w-6 h-6" />
              </div>
              <div>
                <div className="font-bold text-gray-900">Dubbed Video</div>
                <div className="text-sm text-blue-600">
                  MP4 with Hindi audio
                </div>
              </div>
            </div>
            <div className="flex items-center text-blue-600 font-semibold">
              <span className="mr-3 text-sm text-gray-500 bg-white px-2 py-1 rounded border border-blue-100">
                {formatFileSize(downloadData.video.size_bytes)}
              </span>
              <Download className="w-5 h-5 group-hover:translate-y-0.5 transition-transform" />
            </div>
          </a>

          {/* Source Subtitles (English) */}
          <a
            href={downloadData.subtitles.source.url}
            download={downloadData.subtitles.source.filename}
            className="flex items-center justify-between p-4 bg-white rounded-xl border border-gray-200 hover:border-blue-300 hover:shadow-sm transition-all group"
          >
            <div className="flex items-center">
              <div className="bg-gray-100 p-3 rounded-lg text-gray-600 mr-4 group-hover:bg-blue-50 group-hover:text-blue-600 transition-colors">
                <FileText className="w-6 h-6" />
              </div>
              <div>
                <div className="font-semibold text-gray-800">English Subtitles</div>
                <div className="text-sm text-gray-500">SRT format</div>
              </div>
            </div>
            <div className="flex items-center text-gray-400 group-hover:text-blue-600 transition-colors font-medium">
              <span className="mr-3 text-sm">
                {formatFileSize(downloadData.subtitles.source.size_bytes)}
              </span>
              <Download className="w-5 h-5" />
            </div>
          </a>

          {/* Target Subtitles (Hindi) */}
          <a
            href={downloadData.subtitles.target.url}
            download={downloadData.subtitles.target.filename}
            className="flex items-center justify-between p-4 bg-white rounded-xl border border-gray-200 hover:border-blue-300 hover:shadow-sm transition-all group"
          >
            <div className="flex items-center">
              <div className="bg-gray-100 p-3 rounded-lg text-gray-600 mr-4 group-hover:bg-blue-50 group-hover:text-blue-600 transition-colors">
                <FileText className="w-6 h-6" />
              </div>
              <div>
                <div className="font-semibold text-gray-800">Hindi Subtitles</div>
                <div className="text-sm text-gray-500">SRT format (हिन्दी)</div>
              </div>
            </div>
            <div className="flex items-center text-gray-400 group-hover:text-blue-600 transition-colors font-medium">
              <span className="mr-3 text-sm">
                {formatFileSize(downloadData.subtitles.target.size_bytes)}
              </span>
              <Download className="w-5 h-5" />
            </div>
          </a>
        </div>

        {/* Job Info */}
        <div className="mt-6 pt-4 border-t border-gray-200">
          <p className="text-xs text-gray-500 text-center">
            Job ID: {jobId}
          </p>
          <p className="text-xs text-gray-400 text-center mt-1">
            Download links expire in 1 hour
          </p>
        </div>

        {/* Start New Button */}
        <div className="mt-6 text-center">
          <button
            onClick={handleStartNew}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
          >
            Dub Another Video
          </button>
        </div>
      </div>
    </div>
  );
}
