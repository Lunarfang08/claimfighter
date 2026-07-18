'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ArrowLeft, Loader2, RefreshCw, Trash2,
  DollarSign, AlertCircle, TrendingUp, FileText,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ProcessingStatus } from '@/components/upload/ProcessingStatus';
import { RiskReportView } from '@/components/report/RiskReportView';
import { ExtractedFieldsView } from '@/components/report/ExtractedFieldsView';
import { AppealLetterEditor } from '@/components/appeal/AppealLetterEditor';
import { CaseTimeline } from '@/components/timeline/CaseTimeline';
import { FollowUpStatus } from '@/components/followup/FollowUpStatus';
import { useCase, useCaseStatus, useDeleteCase } from '@/hooks/useCases';
import { useQueryClient } from '@tanstack/react-query';

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  uploaded:          { label: 'Uploaded',          className: 'bg-blue-50 text-blue-700 border-blue-200' },
  processing:        { label: 'Processing',        className: 'bg-amber-50 text-amber-700 border-amber-200' },
  completed:         { label: 'Completed',         className: 'bg-green-50 text-green-700 border-green-200' },
  failed:            { label: 'Failed',            className: 'bg-red-50 text-red-700 border-red-200' },
  drafted:           { label: 'Draft Letter Ready',className: 'bg-blue-50 text-blue-700 border-blue-200' },
  approved:          { label: 'Approved',          className: 'bg-violet-50 text-violet-700 border-violet-200' },
  sent:              { label: 'Sent',              className: 'bg-teal-50 text-teal-700 border-teal-200' },
  awaiting_response: { label: 'Awaiting Response', className: 'bg-teal-50 text-teal-800 border-teal-200' },
  escalated:         { label: 'Escalated',         className: 'bg-red-50 text-red-800 border-red-200' },
  resolved:          { label: 'Resolved',          className: 'bg-emerald-50 text-emerald-800 border-emerald-200' },
};

const FOLLOW_UP_STATUSES = ['sent', 'awaiting_response', 'escalated', 'resolved', 'approved', 'drafted'];

function _defaultTab(status: string, hasReport: boolean): string {
  if (['drafted', 'approved', 'sent', 'awaiting_response', 'escalated'].includes(status)) return 'appeal';
  if (status === 'resolved') return 'timeline';
  if (hasReport) return 'report';
  return 'status';
}

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const caseId = params.id as string;

  const { data: caseData, isLoading, error } = useCase(caseId);
  const { data: statusData } = useCaseStatus(caseId, caseData?.status === 'processing');
  const deleteMutation = useDeleteCase();

  // null = user hasn't picked a tab yet; fall back to the status-derived default
  const [selectedTab, setSelectedTab] = useState<string | null>(null);

  useEffect(() => {
    if (statusData?.status === 'completed' || statusData?.status === 'failed' || statusData?.status === 'drafted') {
      queryClient.invalidateQueries({ queryKey: ['case', caseId] });
    }
  }, [statusData?.status, caseId, queryClient]);

  const handleDelete = async () => {
    if (!confirm('Delete this case? This cannot be undone.')) return;
    await deleteMutation.mutateAsync(caseId);
    router.push('/cases');
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Loading case...</p>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="container max-w-4xl mx-auto py-12 px-4">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Case not found or failed to load.{' '}
            <Link href="/cases" className="underline font-medium">Go back to the dashboard</Link>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const status = statusData?.status || caseData.status;
  const steps = statusData?.processing_steps || caseData.processing_steps;
  const badge = STATUS_BADGE[status] || STATUS_BADGE.uploaded;
  const defaultTab = _defaultTab(status, !!caseData.risk_report);
  const report = caseData.risk_report;
  const showFollowUp = FOLLOW_UP_STATUSES.includes(status);

  return (
    <div className="container max-w-5xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="mb-6">
        <Link href="/cases">
          <Button variant="ghost" size="sm" className="mb-4 -ml-2 text-muted-foreground">
            <ArrowLeft className="h-4 w-4 mr-1.5" />
            Back to Dashboard
          </Button>
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight truncate max-w-md">
                {caseData.filename}
              </h1>
              <Badge variant="outline" className={badge.className}>
                {status === 'processing' && <Loader2 className="h-3 w-3 animate-spin mr-1" />}
                {badge.label}
              </Badge>
            </div>
            <p className="text-muted-foreground text-sm mt-1.5">
              Case <span className="font-mono text-xs">{caseId.slice(0, 8)}</span>
              {' · '}
              Submitted{' '}
              {new Date(caseData.created_at).toLocaleDateString('en-US', {
                year: 'numeric', month: 'long', day: 'numeric',
                hour: '2-digit', minute: '2-digit',
              })}
            </p>
          </div>

          <div className="flex gap-2 flex-shrink-0">
            <Button variant="outline" size="sm"
              onClick={() => {
                queryClient.invalidateQueries({ queryKey: ['case', caseId] });
                queryClient.invalidateQueries({ queryKey: ['appeal-letter', caseId] });
                queryClient.invalidateQueries({ queryKey: ['case-timeline', caseId] });
              }}>
              <RefreshCw className="h-4 w-4 mr-1" />Refresh
            </Button>
            <Button variant="destructive" size="sm" onClick={handleDelete} disabled={deleteMutation.isPending}>
              <Trash2 className="h-4 w-4 mr-1" />Delete
            </Button>
          </div>
        </div>

        {/* Key metrics strip */}
        {report && (
          <div className="grid grid-cols-3 gap-3 mt-5">
            <div className="rounded-lg border bg-card px-4 py-3 flex items-center gap-3">
              <DollarSign className="h-4 w-4 text-emerald-600 flex-shrink-0" />
              <div className="min-w-0">
                <div className="font-bold text-emerald-600 truncate">
                  ${parseFloat(report.total_disputed_amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </div>
                <div className="text-xs text-muted-foreground">Disputed</div>
              </div>
            </div>
            <div className="rounded-lg border bg-card px-4 py-3 flex items-center gap-3">
              <FileText className="h-4 w-4 text-primary flex-shrink-0" />
              <div>
                <div className="font-bold">{report.findings.length}</div>
                <div className="text-xs text-muted-foreground">
                  Finding{report.findings.length !== 1 ? 's' : ''}
                </div>
              </div>
            </div>
            <div className="rounded-lg border bg-card px-4 py-3 flex items-center gap-3">
              <TrendingUp className="h-4 w-4 text-primary flex-shrink-0" />
              <div>
                <div className={`font-bold uppercase text-sm ${
                  report.appeal_likelihood === 'high' ? 'text-emerald-600' :
                  report.appeal_likelihood === 'medium' ? 'text-amber-600' : 'text-muted-foreground'
                }`}>
                  {report.appeal_likelihood}
                </div>
                <div className="text-xs text-muted-foreground">Appeal likelihood</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {caseData.error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{caseData.error}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Follow-up status sidebar (only when relevant) */}
        {showFollowUp && (
          <div className="lg:col-span-1 lg:order-2">
            <FollowUpStatus caseData={caseData} />
          </div>
        )}

        {/* Main content */}
        <div className={showFollowUp ? 'lg:col-span-2 lg:order-1' : 'lg:col-span-3'}>
          <Tabs value={selectedTab ?? defaultTab} onValueChange={(v) => setSelectedTab(v as string)}>
            <TabsList className="mb-6 flex-wrap h-auto gap-1">
              <TabsTrigger value="status">Status</TabsTrigger>
              <TabsTrigger value="report" disabled={!caseData.risk_report}>Report</TabsTrigger>
              <TabsTrigger value="fields" disabled={!caseData.extracted_fields}>Data</TabsTrigger>
              <TabsTrigger value="appeal" disabled={!caseData.risk_report}>Appeal Letter</TabsTrigger>
              <TabsTrigger value="timeline">Timeline</TabsTrigger>
            </TabsList>

            <TabsContent value="status">
              <ProcessingStatus steps={steps} currentStatus={status} />
            </TabsContent>

            <TabsContent value="report">
              {caseData.risk_report ? (
                <RiskReportView report={caseData.risk_report} />
              ) : (
                <Card>
                  <CardContent className="py-12 text-center text-muted-foreground">
                    Risk report appears here after processing.
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="fields">
              {caseData.extracted_fields ? (
                <ExtractedFieldsView fields={caseData.extracted_fields} />
              ) : (
                <Card>
                  <CardContent className="py-12 text-center text-muted-foreground">
                    Extracted data appears here after processing.
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="appeal">
              <AppealLetterEditor caseId={caseId} />
            </TabsContent>

            <TabsContent value="timeline">
              <Card>
                <CardHeader>
                  <CardTitle>Case Timeline</CardTitle>
                </CardHeader>
                <CardContent>
                  <CaseTimeline caseId={caseId} />
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
