/**
 * React Query hooks for case management
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  uploadDocument,
  processCase,
  getCases,
  getCase,
  getCaseStatus,
  deleteCase,
} from '@/lib/api';

/**
 * Hook to upload a document
 */
export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => {
      // Invalidate cases list after upload
      queryClient.invalidateQueries({ queryKey: ['cases'] });
    },
  });
}

/**
 * Hook to process a case
 */
export function useProcessCase() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: processCase,
    onSuccess: (_, caseId) => {
      // Invalidate the specific case and the cases list
      queryClient.invalidateQueries({ queryKey: ['case', caseId] });
      queryClient.invalidateQueries({ queryKey: ['cases'] });
    },
  });
}

/**
 * Hook to get all cases
 */
export function useCases(status?: string) {
  return useQuery({
    queryKey: ['cases', status],
    queryFn: () => getCases(status),
  });
}

/**
 * Hook to get a specific case
 */
export function useCase(caseId: string) {
  return useQuery({
    queryKey: ['case', caseId],
    queryFn: () => getCase(caseId),
    enabled: !!caseId,
  });
}

/**
 * Hook to poll case status during processing
 */
export function useCaseStatus(caseId: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ['case-status', caseId],
    queryFn: () => getCaseStatus(caseId),
    enabled: enabled && !!caseId,
    refetchInterval: (query) => {
      // Poll every 2 seconds if status is 'processing'
      const status = query.state.data?.status;
      return status === 'processing' ? 2000 : false;
    },
  });
}

/**
 * Hook to delete a case
 */
export function useDeleteCase() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteCase,
    onSuccess: () => {
      // Invalidate cases list after deletion
      queryClient.invalidateQueries({ queryKey: ['cases'] });
    },
  });
}
