'use client';

import Link from 'next/link';
import { useState } from 'react';
import {
  FileText, Plus, Loader2, AlertCircle,
  CheckCircle2, Clock, XCircle, Trash2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useCases, useDeleteCase } from '@/hooks/useCases';
import type { Case } from '@/lib/types';

const STATUS_CONFIG = {
  uploaded:   { icon: Clock,         color: 'text-blue-500',   badge: 'bg-blue-100 text-blue-800 border-blue-300',     label: 'Uploaded' },
  processing: { icon: Loader2,       color: 'text-yellow-500', badge: 'bg-yellow-100 text-yellow-800 border-yellow-300', label: 'Processing' },
  completed:  { icon: CheckCircle2,  color: 'text-green-500',  badge: 'bg-green-100 text-green-800 border-green-300',   label: 'Completed' },
  failed:     { icon: XCircle,       color: 'text-red-500',    badge: 'bg-red-100 text-red-800 border-red-300',         label: 'Failed' },
  drafted:    { icon: CheckCircle2,  color: 'text-blue-500',   badge: 'bg-blue-100 text-blue-800 border-blue-300',     label: 'Drafted' },
  approved:   { icon: CheckCircle2,  color: 'text-purple-500', badge: 'bg-purple-100 text-purple-800 border-purple-300', label: 'Approved' },
  sent:       { icon: CheckCircle2,  color: 'text-green-500',  badge: 'bg-green-100 text-green-800 border-green-300',   label: 'Sent' },
  awaiting_response: { icon: Clock, color: 'text-green-700',   badge: 'bg-green-50 text-green-900 border-green-300',  label: 'Awaiting Response' },
  escalated:  { icon: XCircle,       color: 'text-red-700',    badge: 'bg-red-50 text-red-900 border-red-300',         label: 'Escalated' },
  resolved:   { icon: CheckCircle2,  color: 'text-emerald-700',badge: 'bg-emerald-50 text-emerald-900 border-emerald-300',label: 'Resolved' },
};

function CaseRow({ c, onDelete }: { c: Case; onDelete: (id: string) => void }) {
  const cfg = STATUS_CONFIG[c.status] || STATUS_CONFIG.uploaded;
  const Icon = cfg.icon;
  const report = c.risk_report;

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-0">
        <div className="flex items-center gap-4 p-4">
          {/* Icon */}
          <div className="flex-shrink-0">
            <Icon className={`h-6 w-6 ${cfg.color} ${c.status === 'processing' ? 'animate-spin' : ''}`} />
          </div>

          {/* Main info — clickable */}
          <Link href={`/cases/${c.case_id}`} className="flex-1 min-w-0 group">
            <div className="flex flex-col sm:flex-row sm:items-center gap-2">
              <span className="font-medium truncate max-w-xs group-hover:text-primary transition-colors">
                {c.filename}
              </span>
              <Badge variant="outline" className={`text-xs w-fit flex-shrink-0 ${cfg.badge}`}>
                {cfg.label}
              </Badge>
            </div>

            <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1 text-xs text-muted-foreground">
              <span>
                {new Date(c.created_at).toLocaleDateString('en-US', {
                  month: 'short', day: 'numeric', year: 'numeric',
                  hour: '2-digit', minute: '2-digit',
                })}
              </span>
              {report && (
                <>
                  <span className="text-green-600 font-medium">
                    ${parseFloat(report.total_disputed_amount).toLocaleString('en-US', {
                      minimumFractionDigits: 2,
                    })} disputed
                  </span>
                  <span>
                    {report.findings.length} finding{report.findings.length !== 1 ? 's' : ''}
                  </span>
                  <span className={
                    report.appeal_likelihood === 'high' ? 'text-green-600 font-medium' :
                    report.appeal_likelihood === 'medium' ? 'text-yellow-600 font-medium' :
                    'text-muted-foreground'
                  }>
                    {report.appeal_likelihood.toUpperCase()} appeal likelihood
                  </span>
                </>
              )}
            </div>
          </Link>

          {/* Delete */}
          <Button
            variant="ghost"
            size="icon"
            className="flex-shrink-0 text-muted-foreground hover:text-destructive"
            onClick={(e) => { e.preventDefault(); onDelete(c.case_id); }}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function CasesPage() {
  const [filter, setFilter] = useState<string | undefined>(undefined);
  const { data, isLoading, error, refetch } = useCases(filter);
  const deleteMutation = useDeleteCase();

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this case? This cannot be undone.')) return;
    await deleteMutation.mutateAsync(id);
  };

  const cases = data?.cases ?? [];

  const counts = {
    all:        data?.total ?? 0,
    completed:  cases.filter((c) => c.status === 'completed').length,
    processing: cases.filter((c) => c.status === 'processing').length,
    failed:     cases.filter((c) => c.status === 'failed').length,
    drafted:    cases.filter((c) => c.status === 'drafted').length,
    approved:   cases.filter((c) => c.status === 'approved').length,
    sent:       cases.filter((c) => c.status === 'sent').length,
    awaiting_response: cases.filter((c) => c.status === 'awaiting_response').length,
    escalated:  cases.filter((c) => c.status === 'escalated').length,
    resolved:   cases.filter((c) => c.status === 'resolved').length,
  };

  return (
    <div className="container max-w-5xl mx-auto py-10 px-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold">Case Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            {data?.total ?? 0} total case{(data?.total ?? 0) !== 1 ? 's' : ''}
          </p>
        </div>
        <Link href="/upload">
          <Button size="lg">
            <Plus className="h-4 w-4 mr-2" />
            New Case
          </Button>
        </Link>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 flex-wrap mb-6">
        {([
          { key: undefined,    label: `All (${counts.all})` },
          { key: 'completed',  label: `Completed (${counts.completed})` },
          { key: 'processing', label: `Processing (${counts.processing})` },
          { key: 'failed',     label: `Failed (${counts.failed})` },
          { key: 'drafted',    label: `Drafted (${counts.drafted})` },
          { key: 'approved',   label: `Approved (${counts.approved})` },
          { key: 'sent',       label: `Sent (${counts.sent})` },
          { key: 'awaiting_response', label: `Awaiting Response (${counts.awaiting_response})` },
          { key: 'escalated',  label: `Escalated (${counts.escalated})` },
          { key: 'resolved',   label: `Resolved (${counts.resolved})` },
        ] as const).map(({ key, label }) => (
          <Button
            key={String(key)}
            variant={filter === key ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter(key)}
          >
            {label}
          </Button>
        ))}
      </div>

      {/* Error state */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load cases.{' '}
            <button className="underline" onClick={() => refetch()}>Retry</button>
          </AlertDescription>
        </Alert>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}

      {/* Empty state */}
      {!isLoading && cases.length === 0 && (
        <div className="text-center py-20">
          <FileText className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
          <h2 className="text-xl font-semibold mb-2">No cases yet</h2>
          <p className="text-muted-foreground mb-6">
            Upload your first medical document to get started.
          </p>
          <Link href="/upload">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Upload Document
            </Button>
          </Link>
        </div>
      )}

      {/* Case list */}
      {!isLoading && cases.length > 0 && (
        <div className="space-y-3">
          {cases.map((c) => (
            <CaseRow key={c.case_id} c={c} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
}
