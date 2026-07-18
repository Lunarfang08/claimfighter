/**
 * React Query hooks for case management — Phases 1-4
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  deleteCase,
  getCase,
  getCases,
  getCaseStatus,
  getCaseTimeline,
  processCase,
  resolveCase,
  escalateCase,
  uploadDocument,
  type ListCasesParams,
} from '@/lib/api';

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cases'] }),
  });
}

export function useProcessCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: processCase,
    onSuccess: (_, caseId) => {
      queryClient.invalidateQueries({ queryKey: ['case', caseId] });
      queryClient.invalidateQueries({ queryKey: ['cases'] });
    },
  });
}

export function useCases(params: ListCasesParams = {}) {
  return useQuery({
    queryKey: ['cases', params],
    queryFn: () => getCases(params),
    staleTime: 10_000,
  });
}

export function useCase(caseId: string) {
  return useQuery({
    queryKey: ['case', caseId],
    queryFn: () => getCase(caseId),
    enabled: !!caseId,
  });
}

export function useCaseStatus(caseId: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ['case-status', caseId],
    queryFn: () => getCaseStatus(caseId),
    enabled: enabled && !!caseId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'processing' ? 2000 : false;
    },
  });
}

export function useCaseTimeline(caseId: string) {
  return useQuery({
    queryKey: ['case-timeline', caseId],
    queryFn: () => getCaseTimeline(caseId),
    enabled: !!caseId,
  });
}

export function useDeleteCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteCase,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cases'] }),
  });
}

export function useResolveCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, payload }: { caseId: string; payload: { outcome: string; notes?: string } }) =>
      resolveCase(caseId, payload),
    onSuccess: (_, { caseId }) => {
      queryClient.invalidateQueries({ queryKey: ['case', caseId] });
      queryClient.invalidateQueries({ queryKey: ['cases'] });
    },
  });
}

export function useEscalateCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, reason }: { caseId: string; reason?: string }) =>
      escalateCase(caseId, reason),
    onSuccess: (_, { caseId }) => {
      queryClient.invalidateQueries({ queryKey: ['case', caseId] });
      queryClient.invalidateQueries({ queryKey: ['appeal-letter', caseId] });
    },
  });
}
