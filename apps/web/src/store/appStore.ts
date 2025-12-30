/**
 * Global app state using Zustand.
 */

import { create } from 'zustand';

type AppStep = 'upload' | 'processing' | 'result';

interface AppState {
  // Current step in the flow
  step: AppStep;
  setStep: (step: AppStep) => void;

  // Current job ID
  jobId: string | null;
  setJobId: (jobId: string | null) => void;

  // Upload progress
  uploadProgress: number;
  setUploadProgress: (progress: number) => void;

  // Error state
  error: string | null;
  setError: (error: string | null) => void;

  // Reset to initial state
  reset: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  step: 'upload',
  setStep: (step) => set({ step }),

  jobId: null,
  setJobId: (jobId) => set({ jobId }),

  uploadProgress: 0,
  setUploadProgress: (uploadProgress) => set({ uploadProgress }),

  error: null,
  setError: (error) => set({ error }),

  reset: () =>
    set({
      step: 'upload',
      jobId: null,
      uploadProgress: 0,
      error: null,
    }),
}));
