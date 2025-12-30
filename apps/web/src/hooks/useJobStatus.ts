/**
 * Hook for polling job status.
 */

import { useQuery } from '@tanstack/react-query';
import { jobService } from '../services/jobService';
import type { Job } from '../types/job';
import { isJobComplete, isJobFailed } from '../types/job';

interface UseJobStatusOptions {
  enabled?: boolean;
  pollingInterval?: number;
}

export function useJobStatus(
  jobId: string | null,
  options: UseJobStatusOptions = {}
) {
  const { enabled = true, pollingInterval = 2000 } = options;

  const query = useQuery<Job, Error>({
    queryKey: ['job', jobId],
    queryFn: () => jobService.getJob(jobId!),
    enabled: enabled && !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Stop polling when job is complete or failed
      if (data && (isJobComplete(data.status) || isJobFailed(data.status))) {
        return false;
      }
      return pollingInterval;
    },
    refetchIntervalInBackground: false,
    retry: 2,
    staleTime: 1000,
  });

  return {
    job: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}
