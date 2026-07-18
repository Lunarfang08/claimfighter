'use client';

import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import {
  useAppealLetter,
  useApproveAppealLetter,
  useSendAppealLetter,
  useUploadInsurerResponse,
} from '@/hooks/useAppealLetter';
import { getAppealLetterPdfUrl } from '@/lib/api';
import type { AppealLetterVersion } from '@/lib/types';
import { Download, FileText, Send, CheckCircle2, Upload } from 'lucide-react';

function statusBadge(status: string) {
  if (status === 'draft')     return 'bg-blue-100 text-blue-800 border-blue-300';
  if (status === 'approved')  return 'bg-purple-100 text-purple-800 border-purple-300';
  if (status === 'sent')      return 'bg-green-100 text-green-800 border-green-300';
  if (status === 'escalated') return 'bg-red-100 text-red-800 border-red-300';
  return 'bg-muted text-foreground border-border';
}

type SendDialogProps = {
  open: boolean;
  onClose: () => void;
  onConfirm: (method: string, deadlineDays: number) => void;
  isPending: boolean;
};

function SendDialog({ open, onClose, onConfirm, isPending }: SendDialogProps) {
  const [method, setMethod] = useState('mail');
  const [days, setDays] = useState(30);
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader><DialogTitle>Mark Letter as Sent</DialogTitle></DialogHeader>
        <div className="space-y-4 py-2">
          <div>
            <label className="text-sm font-medium block mb-2">Delivery Method</label>
            <div className="flex gap-2">
              {['mail', 'email', 'fax'].map((m) => (
                <Button key={m} variant={method === m ? 'default' : 'outline'} size="sm"
                  className="capitalize" onClick={() => setMethod(m)}>
                  {m}
                </Button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Response Deadline (days)</label>
            <div className="flex gap-2">
              {[14, 30, 45, 60].map((d) => (
                <Button key={d} variant={days === d ? 'default' : 'outline'} size="sm"
                  onClick={() => setDays(d)}>
                  {d}d
                </Button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              The system will track this deadline and auto-generate an escalation packet if no response is received.
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isPending}>Cancel</Button>
          <Button onClick={() => onConfirm(method, days)} disabled={isPending}>
            <Send className="h-4 w-4 mr-2" />
            {isPending ? 'Saving...' : 'Confirm Sent'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function AppealLetterEditor({ caseId }: { caseId: string }) {
  const { data, isLoading, error, refetch } = useAppealLetter(caseId);
  const approveMutation = useApproveAppealLetter();
  const sendMutation = useSendAppealLetter();
  const uploadResponseMutation = useUploadInsurerResponse();

  const current = data?.current ?? null;
  const versions = data?.versions ?? [];

  const [editedText, setEditedText] = useState<string>('');
  const [sendDialogOpen, setSendDialogOpen] = useState(false);

  useEffect(() => {
    if (current?.letter_text) {
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
    if (currentStatus === 'draft') return `Edit Draft — Round ${current.round}`;
    if (currentStatus === 'approved') return 'Approved Letter — Ready to Send';
    if (currentStatus === 'sent') return 'Letter Sent — Awaiting Response';
    if (currentStatus === 'escalated') return 'Escalation Packet';
    return 'Appeal Letter';
  }, [currentStatus, current]);

  if (isLoading) {
    return <Card><CardContent className="py-12 text-center text-muted-foreground">Loading appeal letter...</CardContent></Card>;
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>{error instanceof Error ? error.message : 'Failed to load appeal letter.'}</AlertDescription>
      </Alert>
    );
  }

  const isAiEnhanced = current?.metadata?.ai_enhanced === true;

  return (
    <div className="space-y-6">
      {/* Main editor card */}
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="flex items-center justify-between gap-4 flex-wrap">
            <span className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-muted-foreground" />
              {editorHeader}
              {isAiEnhanced && (
                <Badge variant="secondary" className="text-xs font-normal">AI Enhanced</Badge>
              )}
            </span>
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
                No appeal letter exists for this case yet.
                <div className="mt-3">
                  <Button onClick={() => refetch()} variant="outline" size="sm">Retry</Button>
                </div>
              </AlertDescription>
            </Alert>
          ) : (
            <>
              <div className="text-sm text-muted-foreground">
                {currentStatus === 'draft' && 'Edit the letter below, then click "Approve Letter" to lock it in.'}
                {currentStatus === 'approved' && 'This version is approved. Mark it as sent once you\'ve mailed/faxed/emailed it.'}
                {currentStatus === 'sent' && 'Letter sent. Upload the insurer\'s written response to generate a Round 2 draft.'}
                {currentStatus === 'escalated' && 'Escalation packet generated. Review and submit to the appropriate regulator.'}
              </div>

              {currentStatus === 'draft' ? (
                <textarea
                  className="w-full min-h-[360px] rounded-md border bg-background px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/40"
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                />
              ) : (
                <div className="w-full min-h-[360px] whitespace-pre-wrap rounded-md border bg-muted/20 p-4 text-sm font-mono">
                  {current.letter_text}
                </div>
              )}

              {/* Action buttons */}
              <div className="flex gap-3 flex-wrap items-center">
                <Button
                  disabled={!canApprove || approveMutation.isPending}
                  onClick={async () => {
                    if (!current) return;
                    await approveMutation.mutateAsync({ caseId, version_id: current.version_id, letter_text: editedText });
                  }}
                >
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                  {approveMutation.isPending ? 'Approving...' : 'Approve Letter'}
                </Button>

                <Button
                  disabled={!canSend || sendMutation.isPending}
                  variant="outline"
                  onClick={() => setSendDialogOpen(true)}
                >
                  <Send className="h-4 w-4 mr-2" />
                  Mark as Sent
                </Button>

                {/* PDF download */}
                <a
                  href={getAppealLetterPdfUrl(caseId, current.version_id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex"
                >
                  <Button variant="ghost" size="sm">
                    <Download className="h-4 w-4 mr-1.5" />
                    Download PDF
                  </Button>
                </a>

                {responseDeadline && (
                  <Badge variant="secondary" className="ml-auto text-xs">
                    {responseReceivedAt
                      ? `Response received ${new Date(responseReceivedAt).toLocaleDateString('en-US')}`
                      : `Deadline: ${new Date(responseDeadline).toLocaleDateString('en-US')}`
                    }
                  </Badge>
                )}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Insurer response upload (Phase 4) */}
      {current && currentStatus === 'sent' && !responseReceivedAt && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Upload className="h-4 w-4" />
              Upload Insurer Response — Round 2
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Alert>
              <AlertDescription>
                Upload the insurer's written response (PDF, TXT, or image). The system will generate a Round 2 appeal draft automatically.
              </AlertDescription>
            </Alert>
            <div className="flex items-center gap-3 flex-wrap">
              <label
                className={`inline-flex items-center gap-2 rounded-lg border bg-background px-4 py-2 text-sm font-medium shadow-sm transition-colors ${
                  uploadResponseMutation.isPending
                    ? 'opacity-50 cursor-not-allowed'
                    : 'cursor-pointer hover:bg-muted hover:border-primary/40'
                }`}
              >
                <Upload className="h-4 w-4 text-primary" />
                {uploadResponseMutation.isPending ? 'Processing response...' : 'Choose Response File'}
                <input
                  type="file"
                  accept=".pdf,.txt,.png,.jpg,.jpeg"
                  className="sr-only"
                  disabled={uploadResponseMutation.isPending}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    uploadResponseMutation.mutateAsync({ caseId, file })
                      .then(() => setTimeout(() => refetch(), 300))
                      .catch(() => {});
                    e.currentTarget.value = '';
                  }}
                />
              </label>
              {uploadResponseMutation.isPending && (
                <span className="text-sm text-muted-foreground animate-pulse">
                  Analyzing insurer response and drafting Round 2...
                </span>
              )}
            </div>
            {uploadResponseMutation.isError && (
              <Alert variant="destructive">
                <AlertDescription>Upload failed. Please try again.</AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {/* Supporting docs + citations */}
      {current && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader><CardTitle className="text-sm">Supporting Documents Checklist</CardTitle></CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-muted-foreground">
                {(current.supporting_document_checklist ?? []).map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-primary mt-0.5 flex-shrink-0">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-sm">Legal Citations & Policy References</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {current.legal_citations?.length ? (
                <div>
                  <p className="text-xs font-semibold mb-2 text-muted-foreground uppercase tracking-wide">Legal Citations</p>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    {current.legal_citations.map((c, idx) => (
                      <li key={idx} className="break-words leading-relaxed">{c}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {current.policy_references?.length ? (
                <div>
                  <p className="text-xs font-semibold mb-2 text-muted-foreground uppercase tracking-wide">Policy References</p>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    {current.policy_references.map((r, idx) => (
                      <li key={idx} className="break-words leading-relaxed">{r}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {!current.legal_citations?.length && !current.policy_references?.length && (
                <Alert><AlertDescription>No specific citations for this case.</AlertDescription></Alert>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Version history */}
      {versions.length > 1 && (
        <Card>
          <CardHeader><CardTitle className="text-sm">Letter Version History</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              {versions.slice().reverse().map((v: AppealLetterVersion) => (
                <div key={v.version_id} className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="outline" className={statusBadge(v.status)}>{v.status.toUpperCase()}</Badge>
                      <span className="text-xs text-muted-foreground font-mono truncate">{v.version_id}</span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Round {v.round} • {new Date(v.created_at).toLocaleString('en-US')}
                    </div>
                  </div>
                  <a href={getAppealLetterPdfUrl(caseId, v.version_id)} target="_blank" rel="noopener noreferrer">
                    <Button variant="ghost" size="sm" className="text-xs h-7 px-2">
                      <Download className="h-3 w-3 mr-1" />PDF
                    </Button>
                  </a>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Send dialog */}
      <SendDialog
        open={sendDialogOpen}
        onClose={() => setSendDialogOpen(false)}
        isPending={sendMutation.isPending}
        onConfirm={async (method, deadlineDays) => {
          if (!current) return;
          await sendMutation.mutateAsync({
            caseId,
            version_id: current.version_id,
            send_method: method,
            response_deadline_days: deadlineDays,
          });
          setSendDialogOpen(false);
        }}
      />
    </div>
  );
}
