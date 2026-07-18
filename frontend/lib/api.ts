/**
 * API client — Phases 1-4
 */

import axios from 'axios';
import type {
  AppealLetterResponse,
  Case,
  CasesListResponse,
  ProcessResponse,
  TimelineResponse,
  UploadResponse,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

export function getApiErrorMessage(error: unknown, fallback = 'Unknown error'): string {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : fallback;
  }
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === 'object' && item && 'msg' in item ? String(item.msg) : String(item)))
      .join(', ');
  }
  return error.message || fallback;
}

// ── Phase 1 — Upload & Process ────────────────────────────────────────────

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post<UploadResponse>('/api/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function processCase(caseId: string): Promise<ProcessResponse> {
  const { data } = await api.post<ProcessResponse>(`/api/process/${caseId}`);
  return data;
}

// ── Phase 3 — Cases CRUD + Search ────────────────────────────────────────

export interface ListCasesParams {
  status?: string;
  search?: string;
  insurer?: string;
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
}

export async function getCases(params: ListCasesParams = {}): Promise<CasesListResponse> {
  const { data } = await api.get<CasesListResponse>('/api/cases', { params });
  return data;
}

export async function getCase(caseId: string): Promise<Case> {
  const { data } = await api.get<Case>(`/api/cases/${caseId}`);
  return data;
}

export async function getCaseStatus(caseId: string): Promise<{
  case_id: string;
  status: string;
  updated_at: string;
  processing_steps: Case['processing_steps'];
}> {
  const { data } = await api.get(`/api/cases/${caseId}/status`);
  return data;
}

export async function deleteCase(caseId: string): Promise<void> {
  await api.delete(`/api/cases/${caseId}`);
}

// ── Phase 3 — Timeline ────────────────────────────────────────────────────

export async function getCaseTimeline(caseId: string): Promise<TimelineResponse> {
  const { data } = await api.get<TimelineResponse>(`/api/cases/${caseId}/timeline`);
  return data;
}

// ── Phase 2 — Appeal Letters ──────────────────────────────────────────────

export async function getAppealLetter(caseId: string): Promise<AppealLetterResponse> {
  const { data } = await api.get<AppealLetterResponse>(`/api/cases/${caseId}/appeal-letter`);
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
  payload: { version_id: string; send_method?: string; response_deadline_days?: number }
): Promise<{ message: string; version_id: string; response_deadline?: string }> {
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

export function getAppealLetterPdfUrl(caseId: string, versionId: string): string {
  return `${API_BASE_URL}/api/cases/${caseId}/appeal-letter/${versionId}/pdf`;
}

// ── Phase 4 — Follow-up Actions ───────────────────────────────────────────

export async function escalateCase(
  caseId: string,
  reason?: string
): Promise<{ message: string; version_id: string }> {
  const { data } = await api.post(`/api/cases/${caseId}/escalate`, { reason });
  return data;
}

export async function resolveCase(
  caseId: string,
  payload: { outcome: string; notes?: string }
): Promise<{ message: string; case_id: string; outcome: string }> {
  const { data } = await api.post(`/api/cases/${caseId}/resolve`, payload);
  return data;
}
