/**
 * API client for communicating with the FastAPI backend
 */

import axios from 'axios';
import type {
  Case,
  CasesListResponse,
  UploadResponse,
  ProcessResponse,
  AppealLetterVersion,
  ProcessingStep,
  FollowUpState,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/** Extract a human-readable message from FastAPI/Axios errors. */
export function getApiErrorMessage(error: unknown, fallback = 'Unknown error'): string {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : fallback;
  }

  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === 'object' && item && 'msg' in item ? String(item.msg) : String(item)))
      .join(', ');
  }

  return error.message || fallback;
}

/**
 * Upload a document file
 */
export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await api.post<UploadResponse>('/api/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return data;
}

/**
 * Trigger processing for a case
 */
export async function processCase(caseId: string): Promise<ProcessResponse> {
  const { data } = await api.post<ProcessResponse>(`/api/process/${caseId}`);
  return data;
}

/**
 * Get all cases
 */
export async function getCases(status?: string): Promise<CasesListResponse> {
  const params = status ? { status } : {};
  const { data } = await api.get<CasesListResponse>('/api/cases', { params });
  return data;
}

/**
 * Get a specific case by ID
 */
export async function getCase(caseId: string): Promise<Case> {
  const { data } = await api.get<Case>(`/api/cases/${caseId}`);
  return data;
}

/**
 * Get case processing status (for polling)
 */
export async function getCaseStatus(caseId: string): Promise<{
  case_id: string;
  status: string;
  updated_at: string;
  processing_steps: ProcessingStep[];
}> {
  const { data } = await api.get(`/api/cases/${caseId}/status`);
  return data;
}

/**
 * Fetch appeal letter versions for a case.
 */
export async function getAppealLetter(caseId: string): Promise<{
  case_id: string;
  current: AppealLetterVersion | null;
  versions: AppealLetterVersion[];
  follow_up: FollowUpState | null;
}> {
  const { data } = await api.get(`/api/cases/${caseId}/appeal-letter`);
  return data;
}

export async function approveAppealLetter(
  caseId: string,
  payload: { version_id: string; letter_text: string; notes?: string }
): Promise<{ message: string; version_id: string }> {
  const { data } = await api.post(`/api/cases/${caseId}/appeal-letter/approve`, payload);
  return data;
}

export async function sendAppealLetter(
  caseId: string,
  payload: { version_id: string; send_method?: string }
): Promise<{ message: string; version_id: string }> {
  const { data } = await api.post(`/api/cases/${caseId}/appeal-letter/send`, payload);
  return data;
}

export async function uploadInsurerResponse(
  caseId: string,
  file: File
): Promise<{ message: string; version_id?: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post(`/api/cases/${caseId}/insurer-response`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

/**
 * Delete a case
 */
export async function deleteCase(caseId: string): Promise<void> {
  await api.delete(`/api/cases/${caseId}`);
}
