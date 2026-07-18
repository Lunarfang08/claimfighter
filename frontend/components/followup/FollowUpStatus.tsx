'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { useEscalateCase, useResolveCase } from '@/hooks/useCases';
import type { Case, FollowUpState, ResolutionOutcome } from '@/lib/types';
import { AlertTriangle, CheckCircle2, Clock, Send, XCircle } from 'lucide-react';

const AGENT_STATE_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  idle:              { label: 'Idle',              color: 'bg-gray-100 text-gray-700',    icon: <Clock className="h-3 w-3" /> },
  letter_sent:       { label: 'Awaiting Response', color: 'bg-blue-100 text-blue-800',   icon: <Send className="h-3 w-3" /> },
  draft_round2:      { label: 'Round 2 Ready',     color: 'bg-orange-100 text-orange-800', icon: <AlertTriangle className="h-3 w-3" /> },
  draft_escalation:  { label: 'Escalation Ready',  color: 'bg-red-100 text-red-800',     icon: <AlertTriangle className="h-3 w-3" /> },
  escalated:         { label: 'Escalated',          color: 'bg-red-100 text-red-800',     icon: <XCircle className="h-3 w-3" /> },
  resolved:          { label: 'Resolved',           color: 'bg-emerald-100 text-emerald-800', icon: <CheckCircle2 className="h-3 w-3" /> },
};

function DeadlineBadge({ deadline, received }: { deadline: string | null | undefined; received: string | null | undefined }) {
  if (!deadline) return null;
  const dt = new Date(deadline);
  const now = new Date();
  const isPast = dt < now && !received;
  const isClose = !isPast && dt.getTime() - now.getTime() < 7 * 24 * 60 * 60 * 1000;

  return (
    <div className={`text-xs rounded-md px-2 py-1 inline-flex items-center gap-1.5 border ${
      isPast ? 'bg-red-50 border-red-300 text-red-700' :
      isClose ? 'bg-yellow-50 border-yellow-300 text-yellow-700' :
      'bg-gray-50 border-gray-200 text-gray-600'
    }`}>
      <Clock className="h-3 w-3" />
      {received
        ? `Response received ${new Date(received).toLocaleDateString('en-US')}`
        : isPast
          ? `Deadline passed: ${dt.toLocaleDateString('en-US')}`
          : `Deadline: ${dt.toLocaleDateString('en-US')}`
      }
    </div>
  );
}

type ResolveDialogProps = {
  open: boolean;
  onClose: () => void;
  onConfirm: (outcome: ResolutionOutcome, notes: string) => void;
  isPending: boolean;
};

function ResolveDialog({ open, onClose, onConfirm, isPending }: ResolveDialogProps) {
  const [outcome, setOutcome] = useState<ResolutionOutcome>('won');
  const [notes, setNotes] = useState('');

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Resolve Case</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div>
            <label className="text-sm font-medium block mb-2">Outcome</label>
            <div className="flex gap-2">
              {(['won', 'partial', 'lost'] as const).map((o) => (
                <Button
                  key={o}
                  variant={outcome === o ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setOutcome(o)}
                  className="capitalize"
                >
                  {o}
                </Button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Notes (optional)</label>
            <textarea
              className="w-full rounded-md border bg-background px-3 py-2 text-sm min-h-[80px] focus:outline-none focus:ring-2 focus:ring-primary/40"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="What was the final outcome? How much was recovered?"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isPending}>Cancel</Button>
          <Button onClick={() => onConfirm(outcome, notes)} disabled={isPending}>
            {isPending ? 'Saving...' : 'Mark Resolved'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function FollowUpStatus({ caseData }: { caseData: Case }) {
  const [resolveOpen, setResolveOpen] = useState(false);
  const resolveMutation = useResolveCase();
  const escalateMutation = useEscalateCase();

  const followUp = caseData.follow_up;
  const status = caseData.status;

  const agentState = followUp?.agent_state ?? 'idle';
  const cfg = AGENT_STATE_CONFIG[agentState] ?? AGENT_STATE_CONFIG.idle;

  const canEscalate = ['sent', 'drafted', 'approved', 'awaiting_response'].includes(status);
  const canResolve = !['uploaded', 'processing', 'failed', 'resolved'].includes(status);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-3 flex-wrap">
          <span>Follow-up Loop</span>
          <Badge className={`${cfg.color} border gap-1.5 text-xs font-medium`} variant="outline">
            {cfg.icon}
            {cfg.label}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Deadline badges */}
        {followUp && (
          <div className="space-y-2">
            {followUp.round_1_response_deadline && (
              <DeadlineBadge
                deadline={followUp.round_1_response_deadline}
                received={followUp.round_1_response_received_at}
              />
            )}
            {followUp.round_2_response_deadline && (
              <div className="text-xs text-muted-foreground">
                Round 2 deadline: {new Date(followUp.round_2_response_deadline).toLocaleDateString('en-US')}
              </div>
            )}
          </div>
        )}

        {/* Round info */}
        {followUp && followUp.round > 0 && (
          <div className="text-sm text-muted-foreground space-y-1">
            <div>Round: <span className="font-medium text-foreground">{followUp.round}</span></div>
            {followUp.round_1_sent_at && (
              <div>
                Sent: <span className="font-medium text-foreground">
                  {new Date(followUp.round_1_sent_at).toLocaleDateString('en-US')}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Resolution summary */}
        {caseData.resolution && (
          <Alert className="border-emerald-200 bg-emerald-50">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <AlertDescription className="text-emerald-900">
              <strong className="capitalize">Case {caseData.resolution.outcome}</strong>
              {caseData.resolution.notes && (
                <span className="block text-sm mt-1">{caseData.resolution.notes}</span>
              )}
              <span className="block text-xs mt-1 text-emerald-700">
                Resolved {new Date(caseData.resolution.resolved_at).toLocaleDateString('en-US')}
              </span>
            </AlertDescription>
          </Alert>
        )}

        {/* Action buttons */}
        <div className="flex gap-2 flex-wrap pt-2">
          {canEscalate && !caseData.follow_up?.escalation_ready && (
            <Button
              variant="destructive"
              size="sm"
              disabled={escalateMutation.isPending}
              onClick={() => escalateMutation.mutate({ caseId: caseData.case_id, reason: 'manual_escalation' })}
            >
              {escalateMutation.isPending ? 'Escalating...' : 'Escalate Case'}
            </Button>
          )}
          {canResolve && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setResolveOpen(true)}
            >
              Resolve Case
            </Button>
          )}
        </div>

        {escalateMutation.isError && (
          <Alert variant="destructive" className="text-xs">
            <AlertDescription>Escalation failed. Please try again.</AlertDescription>
          </Alert>
        )}
      </CardContent>

      <ResolveDialog
        open={resolveOpen}
        onClose={() => setResolveOpen(false)}
        isPending={resolveMutation.isPending}
        onConfirm={async (outcome, notes) => {
          await resolveMutation.mutateAsync({ caseId: caseData.case_id, payload: { outcome, notes } });
          setResolveOpen(false);
        }}
      />
    </Card>
  );
}
