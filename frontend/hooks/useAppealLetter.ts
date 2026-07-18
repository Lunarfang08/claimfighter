/**
 * React Query hooks for appeal letter workflow — Phases 2 & 4
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  approveAppealLetter,
  getAppealLetter,
  sendAppealLetter,
  uploadInsurerResponse,
} from '@/lib/api';

export function useAppealLetter(caseId: string | undefined) {
  return useQuery({
    queryKey: ['appeal-letter', caseId],
    queryFn: () => {
      if (!caseId) throw new Error('caseId is required');
      return getAppealLetter(caseId);
    },
    enabled: !!caseId,
  });
}

export function useApproveAppealLetter() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      caseId,
      version_id,
      letter_text,
      notes,
    }: {
      caseId: string;
      version_id: string;
      letter_text: string;
      notes?: string;
    }) => approveAppealLetter(caseId, { version_id, letter_text, notes }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['case', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['appeal-letter', variables.caseId] });
    },
  });
}

export function useSendAppealLetter() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      caseId,
      version_id,
      send_method,
      response_deadline_days,
    }: {
      caseId: string;
      version_id: string;
      send_method?: string;
      response_deadline_days?: number;
    }) => sendAppealLetter(caseId, { version_id, send_method, response_deadline_days }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['case', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['appeal-letter', variables.caseId] });
    },
  });
}

export function useUploadInsurerResponse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ caseId, file }: { caseId: string; file: File }) =>
      uploadInsurerResponse(caseId, file),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['case', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['appeal-letter', variables.caseId] });
      queryClient.invalidateQueries({ queryKey: ['case-timeline', variables.caseId] });
    },
  });
}
