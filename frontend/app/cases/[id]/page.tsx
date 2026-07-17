'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import Link from 'next/link';
import { ArrowLeft, Loader2, RefreshCw, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ProcessingStatus } from '@/components/upload/ProcessingStatus';
import { RiskReportView } from '@/components/report/RiskReportView';
import { ExtractedFieldsView } from '@/components/report/ExtractedFieldsView';
import { useCase, useCaseStatus, useDeleteCase } from '@/hooks/useCases';
import { AppealLetterEditor } from '@/components/appeal/AppealLetterEditor';
import { useQueryClient } from '@tanstack/react-query';

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  uploaded:   { label: 'Uploaded',   className: 'bg-blue-100 text-blue-800 border-blue-300' },
  processing: { label: 'Processing', className: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
  completed:  { label: 'Completed',  className: 'bg-green-100 text-green-800 border-green-300' },
  failed:     { label: 'Failed',     className: 'bg-red-100 text-red-800 border-red-300' },
  drafted:    { label: 'Draft Letter Ready', className: 'bg-blue-100 text-blue-800 border-blue-300' },
  approved:   { label: 'Approved', className: 'bg-purple-100 text-purple-800 border-purple-300' },
  sent:       { label: 'Sent', className: 'bg-green-100 text-green-800 border-green-300' },
  awaiting_response: { label: 'Awaiting Response', className: 'bg-green-50 text-green-900 border-green-300' },
  escalated:  { label: 'Escalated', className: 'bg-red-50 text-red-900 border-red-300' },
  resolved:   { label: 'Resolved', className: 'bg-emerald-50 text-emerald-900 border-emerald-300' },
};

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const caseId = params.id as string;

  const { data: caseData, isLoading, error } = useCase(caseId);
  const { data: statusData } = useCaseStatus(
    caseId,
    caseData?.status === 'processing'
  );
  const deleteMutation = useDeleteCase();

  // Refresh full case data when status polling indicates completion
  useEffect(() => {
    if (statusData?.status === 'completed' || statusData?.status === 'failed') {
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
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="container max-w-4xl mx-auto py-12 px-4">
        <Alert variant="destructive">
          <AlertDescription>
            Case not found or failed to load.{' '}
            <Link href="/cases" className="underline">Go back to cases</Link>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const status = statusData?.status || caseData.status;
  const steps  = statusData?.processing_steps || caseData.processing_steps;
  const badge  = STATUS_BADGE[status] || STATUS_BADGE.uploaded;

  return (
    <div className="container max-w-5xl mx-auto py-10 px-4">
      {/* Header */}
      <div className="mb-8">
        <Link href="/cases">
          <Button variant="ghost" className="mb-4 -ml-2">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Cases
          </Button>
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-3xl font-bold truncate max-w-md">
                {caseData.filename}
              </h1>
              <Badge variant="outline" className={badge.className}>
                {status === 'processing' && (
                  <Loader2 className="h-3 w-3 animate-spin mr-1" />
                )}
                {badge.label}
              </Badge>
            </div>
            <p className="text-muted-foreground text-sm mt-1">
              Case ID: <span className="font-mono text-xs">{caseId}</span>
            </p>
            <p className="text-muted-foreground text-sm">
              Submitted{' '}
              {new Date(caseData.created_at).toLocaleDateString('en-US', {
                year: 'numeric', month: 'long', day: 'numeric',
                hour: '2-digit', minute: '2-digit',
              })}
            </p>
          </div>

          <div className="flex gap-2 flex-shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => queryClient.invalidateQueries({ queryKey: ['case', caseId] })}
            >
              <RefreshCw className="h-4 w-4 mr-1" />
              Refresh
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Delete
            </Button>
          </div>
        </div>
      </div>

      {/* Error banner */}
      {caseData.error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{caseData.error}</AlertDescription>
        </Alert>
      )}

      {/* Main content tabs */}
      <Tabs
        defaultValue={
          caseData.status === 'drafted' ||
          caseData.status === 'approved' ||
          caseData.status === 'sent'
            ? 'appeal'
            : caseData.risk_report
              ? 'report'
              : 'status'
        }
      >
        <TabsList className="mb-6">
          <TabsTrigger value="status">Processing Status</TabsTrigger>
          <TabsTrigger value="report" disabled={!caseData.risk_report}>
            Risk Report
          </TabsTrigger>
          <TabsTrigger value="fields" disabled={!caseData.extracted_fields}>
            Extracted Data
          </TabsTrigger>
          <TabsTrigger value="appeal" disabled={!caseData.risk_report}>
            Appeal Letter
          </TabsTrigger>
        </TabsList>

        {/* Processing Status Tab */}
        <TabsContent value="status">
          <ProcessingStatus steps={steps} currentStatus={status} />
        </TabsContent>

        {/* Risk Report Tab */}
        <TabsContent value="report">
          {caseData.risk_report ? (
            <RiskReportView report={caseData.risk_report} />
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                Risk report will appear here after processing completes.
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Extracted Fields Tab */}
        <TabsContent value="fields">
          {caseData.extracted_fields ? (
            <ExtractedFieldsView fields={caseData.extracted_fields} />
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                Extracted data will appear here after processing completes.
              </CardContent>
            </Card>
          )}
        </TabsContent>

          {/* Appeal Letter Tab (Phase 2+) */}
        <TabsContent value="appeal">
          <Card className="border-dashed">
            <CardHeader>
              <CardTitle className="text-muted-foreground">Appeal Letter Editor</CardTitle>
            </CardHeader>
            <CardContent className="py-6">
              <AppealLetterEditor caseId={caseId} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
