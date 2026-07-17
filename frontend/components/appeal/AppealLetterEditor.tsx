'use client';

import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useAppealLetter, useApproveAppealLetter, useSendAppealLetter, useUploadInsurerResponse } from '@/hooks/useAppealLetter';
import type { AppealLetterVersion } from '@/lib/types';

function statusBadge(status: string) {
  if (status === 'draft') return 'bg-blue-100 text-blue-800 border-blue-300';
  if (status === 'approved') return 'bg-purple-100 text-purple-800 border-purple-300';
  if (status === 'sent') return 'bg-green-100 text-green-800 border-green-300';
  if (status === 'escalated') return 'bg-red-100 text-red-800 border-red-300';
  return 'bg-muted text-foreground border-border';
}

export function AppealLetterEditor({ caseId }: { caseId: string }) {
  const { data, isLoading, error, refetch } = useAppealLetter(caseId);
  const approveMutation = useApproveAppealLetter();
  const sendMutation = useSendAppealLetter();
  const uploadResponseMutation = useUploadInsurerResponse();

  const current = data?.current ?? null;
  const versions = data?.versions ?? [];

  const [editedText, setEditedText] = useState<string>('');
  useEffect(() => {
    if (current?.letter_text) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setEditedText(current.letter_text);
    }
  }, [current?.version_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const currentStatus = current?.status ?? 'draft';
  const canApprove = currentStatus === 'draft';
  const canSend = currentStatus === 'approved';

  const followUp = data?.follow_up;
  const responseDeadline = followUp?.round_1_response_deadline;
  const responseReceivedAt = followUp?.round_1_response_received_at;

  const editorHeader = useMemo(() => {
    if (!current) return 'Appeal Letter';
    if (currentStatus === 'draft') return 'Edit Draft (Phase 2)';
    if (currentStatus === 'approved') return 'Approved Letter (Ready to Send)';
    if (currentStatus === 'sent') return 'Letter Sent (Phase 5 Follow-up)';
    return 'Appeal Letter';
  }, [currentStatus, current]);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">Loading appeal letter...</CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          {error instanceof Error ? error.message : 'Failed to load appeal letter.'}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="flex items-center justify-between gap-4">
            <span>{editorHeader}</span>
            {current ? (
              <Badge variant="outline" className={statusBadge(currentStatus)}>
                {currentStatus.toUpperCase()}
              </Badge>
            ) : (
              <Badge variant="outline" className={statusBadge('draft')}>NO LETTER</Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {!current ? (
            <Alert variant="destructive">
              <AlertDescription>
                No appeal letter draft exists for this case. Processing may not have reached Phase 2 yet.
              </AlertDescription>
              <div className="mt-3">
                <Button onClick={() => refetch()} variant="outline" disabled={approveMutation.isPending || sendMutation.isPending}>
                  Retry
                </Button>
              </div>
            </Alert>
          ) : (
            <>
              <div className="text-sm text-muted-foreground">
                {currentStatus === 'draft' && 'Edit below, then click “Approve Letter” to create the approved version.'}
                {currentStatus === 'approved' && 'This version is approved. Click “Mark as Sent” when you mail/fax/email it.'}
                {currentStatus === 'sent' && 'You marked this letter as sent. Upload insurer responses to trigger round 2.'}
              </div>

              {currentStatus === 'draft' ? (
                <textarea
                  className="w-full min-h-[320px] rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                />
              ) : (
                <div className="w-full min-h-[320px] whitespace-pre-wrap rounded-md border bg-muted/20 p-4 text-sm">
                  {current.letter_text}
                </div>
              )}

              <div className="flex gap-3 flex-wrap items-center">
                <Button
                  disabled={!canApprove || approveMutation.isPending}
                  onClick={async () => {
                    if (!current) return;
                    await approveMutation.mutateAsync({
                      caseId,
                      version_id: current.version_id,
                      letter_text: editedText,
                    });
                  }}
                >
                  {approveMutation.isPending ? 'Approving...' : 'Approve Letter'}
                </Button>

                <Button
                  disabled={!canSend || sendMutation.isPending}
                  variant="outline"
                  onClick={async () => {
                    if (!current) return;
                    await sendMutation.mutateAsync({
                      caseId,
                      version_id: current.version_id,
                      send_method: 'mail',
                    });
                  }}
                >
                  {sendMutation.isPending ? 'Marking Sent...' : 'Mark as Sent'}
                </Button>

                {responseDeadline && (
                  <Badge variant="secondary" className="ml-auto">
                    Response deadline: {new Date(responseDeadline).toLocaleDateString('en-US')}
                  </Badge>
                )}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {current && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {currentStatus === 'sent' && responseDeadline && !responseReceivedAt && (
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Upload Insurer Response (Round 2)</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Alert>
                  <AlertDescription>
                    Upload the insurer’s written response. The backend will generate a Round 2 draft appeal letter.
                  </AlertDescription>
                </Alert>

                <div className="flex items-center gap-3 flex-wrap">
                  <input
                    type="file"
                    accept=".pdf,.txt,.png,.jpg,.jpeg"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      uploadResponseMutation
                        .mutateAsync({ caseId, file })
                        .then(() => {
                          setTimeout(() => refetch(), 200);
                        })
                        .catch(() => {});
                      e.currentTarget.value = '';
                    }}
                    disabled={uploadResponseMutation.isPending}
                  />

                  <Button
                    type="button"
                    variant="outline"
                    disabled={uploadResponseMutation.isPending}
                    onClick={() => {
                      // File input triggers mutation directly on selection.
                    }}
                  >
                    {uploadResponseMutation.isPending ? 'Processing...' : 'Choose File'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Supporting Documents Checklist</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-muted-foreground">
                {(current.supporting_document_checklist ?? []).map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-primary mt-0.5">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Legal Citations & Policy References</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {current.legal_citations?.length ? (
                <div>
                  <div className="text-sm font-semibold mb-2">Legal Citations</div>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    {current.legal_citations.map((c, idx) => (
                      <li key={idx} className="break-words">
                        {c}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <Alert>
                  <AlertDescription>No specific legal citations were extracted for this case.</AlertDescription>
                </Alert>
              )}

              {current.policy_references?.length ? (
                <div>
                  <div className="text-sm font-semibold mb-2">Policy References</div>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    {current.policy_references.map((c, idx) => (
                      <li key={idx} className="break-words">
                        {c}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>
      )}

      {versions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Letter Versions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {versions
                .slice()
                .reverse()
                .map((v: AppealLetterVersion) => (
                  <div key={v.version_id} className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant="outline" className={statusBadge(v.status)}>{v.status.toUpperCase()}</Badge>
                        <span className="text-sm font-medium truncate">{v.version_id}</span>
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        Round {v.round} • {new Date(v.created_at).toLocaleString('en-US')}
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

