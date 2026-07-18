'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import {
  FileText, Plus, Loader2, AlertCircle, CheckCircle2, Clock,
  XCircle, Trash2, Search, X, DollarSign, FolderOpen, Scale,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useCases, useDeleteCase } from '@/hooks/useCases';
import type { Case } from '@/lib/types';

const STATUS_CONFIG = {
  uploaded:          { icon: Clock,        color: 'text-blue-500',    badge: 'bg-blue-50 text-blue-700 border-blue-200',          label: 'Uploaded' },
  processing:        { icon: Loader2,      color: 'text-amber-500',   badge: 'bg-amber-50 text-amber-700 border-amber-200',       label: 'Processing' },
  completed:         { icon: CheckCircle2, color: 'text-green-500',   badge: 'bg-green-50 text-green-700 border-green-200',       label: 'Completed' },
  failed:            { icon: XCircle,      color: 'text-red-500',     badge: 'bg-red-50 text-red-700 border-red-200',             label: 'Failed' },
  drafted:           { icon: FileText,     color: 'text-primary',     badge: 'bg-blue-50 text-blue-700 border-blue-200',          label: 'Draft Ready' },
  approved:          { icon: CheckCircle2, color: 'text-violet-500',  badge: 'bg-violet-50 text-violet-700 border-violet-200',    label: 'Approved' },
  sent:              { icon: CheckCircle2, color: 'text-teal-600',    badge: 'bg-teal-50 text-teal-700 border-teal-200',          label: 'Sent' },
  awaiting_response: { icon: Clock,        color: 'text-teal-700',    badge: 'bg-teal-50 text-teal-800 border-teal-200',          label: 'Awaiting Response' },
  escalated:         { icon: Scale,        color: 'text-red-600',     badge: 'bg-red-50 text-red-800 border-red-200',             label: 'Escalated' },
  resolved:          { icon: CheckCircle2, color: 'text-emerald-600', badge: 'bg-emerald-50 text-emerald-800 border-emerald-200', label: 'Resolved' },
} as const;

function CaseRow({ c, onDelete, isDeleting }: { c: Case; onDelete: (id: string) => void; isDeleting: boolean }) {
  const cfg = STATUS_CONFIG[c.status as keyof typeof STATUS_CONFIG] ?? STATUS_CONFIG.uploaded;
  const Icon = cfg.icon;
  const report = c.risk_report;

  return (
    <Card className="group hover:shadow-md hover:border-primary/30 transition-all duration-150">
      <CardContent className="p-0">
        <div className="flex items-center gap-4 p-4">
          <div className={`flex-shrink-0 p-2 rounded-lg bg-muted/60 ${cfg.color}`}>
            <Icon className={`h-5 w-5 ${c.status === 'processing' ? 'animate-spin' : ''}`} />
          </div>

          <Link href={`/cases/${c.case_id}`} className="flex-1 min-w-0">
            <div className="flex flex-col sm:flex-row sm:items-center gap-2">
              <span className="font-medium truncate max-w-xs group-hover:text-primary transition-colors">
                {c.filename}
              </span>
              <Badge variant="outline" className={`text-xs w-fit flex-shrink-0 ${cfg.badge}`}>
                {cfg.label}
              </Badge>
            </div>

            <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1.5 text-xs text-muted-foreground">
              <span>
                {new Date(c.created_at).toLocaleDateString('en-US', {
                  month: 'short', day: 'numeric', year: 'numeric',
                  hour: '2-digit', minute: '2-digit',
                })}
              </span>
              {report && (
                <>
                  <span className="text-emerald-600 font-semibold">
                    ${parseFloat(report.total_disputed_amount).toLocaleString('en-US', { minimumFractionDigits: 2 })} disputed
                  </span>
                  <span>{report.findings.length} finding{report.findings.length !== 1 ? 's' : ''}</span>
                  <span className={
                    report.appeal_likelihood === 'high' ? 'text-emerald-600 font-medium' :
                    report.appeal_likelihood === 'medium' ? 'text-amber-600 font-medium' :
                    'text-muted-foreground'
                  }>
                    {report.appeal_likelihood.toUpperCase()} likelihood
                  </span>
                </>
              )}
              {c.extracted_fields?.insurer_name && (
                <span className="truncate max-w-[180px]">{c.extracted_fields.insurer_name}</span>
              )}
            </div>
          </Link>

          <div className="flex items-center gap-1 flex-shrink-0">
            <Button
              variant="ghost" size="icon"
              className="text-muted-foreground hover:text-destructive opacity-60 group-hover:opacity-100 transition-opacity"
              disabled={isDeleting}
              onClick={(e) => { e.preventDefault(); onDelete(c.case_id); }}
              aria-label="Delete case"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
            <ChevronRight className="h-4 w-4 text-muted-foreground/40 group-hover:text-primary transition-colors hidden sm:block" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function CaseRowSkeleton() {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-4 animate-pulse">
          <div className="h-9 w-9 rounded-lg bg-muted flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-muted rounded w-1/3" />
            <div className="h-3 bg-muted rounded w-2/3" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function StatCard({ icon: Icon, label, value, accent }: {
  icon: React.ElementType; label: string; value: string; accent?: string;
}) {
  return (
    <Card>
      <CardContent className="py-4 px-5 flex items-center gap-3">
        <div className={`p-2 rounded-lg bg-primary/10 ${accent ?? 'text-primary'}`}>
          <Icon className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <div className="text-xl font-bold leading-tight truncate">{value}</div>
          <div className="text-xs text-muted-foreground">{label}</div>
        </div>
      </CardContent>
    </Card>
  );
}

const STATUS_FILTERS = [
  { key: undefined,           label: 'All' },
  { key: 'drafted',           label: 'Draft Ready' },
  { key: 'approved',          label: 'Approved' },
  { key: 'sent',              label: 'Sent' },
  { key: 'awaiting_response', label: 'Awaiting Response' },
  { key: 'escalated',         label: 'Escalated' },
  { key: 'resolved',          label: 'Resolved' },
  { key: 'processing',        label: 'Processing' },
  { key: 'failed',            label: 'Failed' },
] as const;

export default function CasesPage() {
  const [filter, setFilter] = useState<string | undefined>(undefined);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const deleteMutation = useDeleteCase();

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 350);
    return () => clearTimeout(t);
  }, [search]);

  const { data, isLoading, error, refetch } = useCases({
    status: filter,
    search: debouncedSearch || undefined,
    limit: 100,
    sort_by: 'created_at',
    sort_dir: 'desc',
  });

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this case? This cannot be undone.')) return;
    await deleteMutation.mutateAsync(id);
  };

  const cases = data?.cases ?? [];

  const totalDisputed = cases.reduce(
    (sum, c) => sum + (c.risk_report ? parseFloat(c.risk_report.total_disputed_amount) || 0 : 0),
    0
  );
  const activeCases = cases.filter((c) =>
    ['drafted', 'approved', 'sent', 'awaiting_response', 'escalated'].includes(c.status)
  ).length;
  const resolvedCases = cases.filter((c) => c.status === 'resolved').length;

  return (
    <div className="container max-w-5xl mx-auto py-10 px-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Case Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Track every appeal from upload to resolution.
          </p>
        </div>
        <Link href="/upload">
          <Button size="lg" className="shadow-sm">
            <Plus className="h-4 w-4 mr-2" />
            New Case
          </Button>
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
        <StatCard icon={FolderOpen} label="Total cases" value={String(data?.total ?? 0)} />
        <StatCard
          icon={DollarSign}
          label="Disputed on this page"
          value={`$${totalDisputed.toLocaleString('en-US', { maximumFractionDigits: 0 })}`}
          accent="text-emerald-600"
        />
        <StatCard icon={Clock} label="Active appeals" value={String(activeCases)} accent="text-amber-600" />
        <StatCard icon={CheckCircle2} label="Resolved" value={String(resolvedCases)} accent="text-emerald-600" />
      </div>

      {/* Search bar */}
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        <input
          className="w-full pl-9 pr-9 py-2.5 text-sm rounded-lg border bg-card shadow-sm focus:outline-none focus:ring-2 focus:ring-ring/40 focus:border-ring transition-shadow"
          placeholder="Search by filename, patient name, or insurer..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {search && (
          <button
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            onClick={() => setSearch('')}
            aria-label="Clear search"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Status filter tabs */}
      <div className="flex gap-2 flex-wrap mb-6">
        {STATUS_FILTERS.map(({ key, label }) => (
          <Button
            key={String(key)}
            variant={filter === key ? 'default' : 'outline'}
            size="sm"
            className="rounded-full"
            onClick={() => setFilter(key)}
          >
            {label}
          </Button>
        ))}
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load cases. The server may be waking up — please{' '}
            <button className="underline font-medium" onClick={() => refetch()}>retry</button>.
          </AlertDescription>
        </Alert>
      )}

      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => <CaseRowSkeleton key={i} />)}
        </div>
      )}

      {!isLoading && !error && cases.length === 0 && (
        <div className="text-center py-20 rounded-xl border border-dashed bg-muted/20">
          <div className="inline-flex p-4 rounded-2xl bg-primary/10 text-primary mb-4">
            <FileText className="h-8 w-8" />
          </div>
          <h2 className="text-xl font-semibold mb-2">
            {debouncedSearch || filter ? 'No matching cases' : 'No cases yet'}
          </h2>
          <p className="text-muted-foreground mb-6 max-w-sm mx-auto">
            {debouncedSearch
              ? `No cases match "${debouncedSearch}". Try a different search.`
              : filter
                ? 'No cases with this status. Try another filter.'
                : 'Upload your first denial letter, EOB, or itemized bill to get started.'}
          </p>
          {!debouncedSearch && !filter && (
            <Link href="/upload">
              <Button><Plus className="h-4 w-4 mr-2" />Upload Document</Button>
            </Link>
          )}
        </div>
      )}

      {!isLoading && cases.length > 0 && (
        <div className="space-y-3">
          {cases.map((c) => (
            <CaseRow
              key={c.case_id}
              c={c}
              onDelete={handleDelete}
              isDeleting={deleteMutation.isPending}
            />
          ))}
        </div>
      )}
    </div>
  );
}
