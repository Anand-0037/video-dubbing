/**
 * API client for DubWizard backend.
 */

import axios, { AxiosError, AxiosInstance } from 'axios';
import type { ApiError, ApiResponse } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      timeout: 30000,
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiResponse<unknown>>) => {
        if (error.response?.data) {
          return Promise.reject(error.response.data);
        }
        return Promise.reject({
          success: false,
          data: null,
          error: {
            code: 'NETWORK_ERROR',
            message: error.message || 'Network error occurred',
          },
        } as ApiResponse<unknown>);
      }
    );
  }

  async get<T>(url: string): Promise<ApiResponse<T>> {
    const response = await this.client.get<ApiResponse<T>>(url);
    return response.data;
  }

  async post<T>(url: string, data?: unknown): Promise<ApiResponse<T>> {
    const response = await this.client.post<ApiResponse<T>>(url, data);
    return response.data;
  }

  async delete<T>(url: string): Promise<ApiResponse<T>> {
    const response = await this.client.delete<ApiResponse<T>>(url);
    return response.data;
  }
}

export const apiClient = new ApiClient();

// Helper to extract data or throw error
export function unwrapResponse<T>(response: ApiResponse<T>): T {
  if (!response.success || response.data === null) {
    throw response.error || { code: 'UNKNOWN_ERROR', message: 'Unknown error' };
  }
  return response.data;
}

// Helper to format API errors for display
export function formatApiError(error: unknown): string {
  if (typeof error === 'object' && error !== null) {
    const apiError = error as ApiError | ApiResponse<unknown>;
    if ('message' in apiError) {
      return apiError.message;
    }
    if ('error' in apiError && apiError.error) {
      return apiError.error.message;
    }
  }
  return 'An unexpected error occurred';
}
