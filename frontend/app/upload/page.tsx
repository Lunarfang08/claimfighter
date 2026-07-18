'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { FileUploader } from '@/components/upload/FileUploader';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  CheckCircle2, AlertCircle, ArrowLeft, Loader2,
  FileUp, Sparkles, FileSearch, ShieldCheck,
} from 'lucide-react';
import { useUploadDocument, useProcessCase } from '@/hooks/useCases';
import { getApiErrorMessage } from '@/lib/api';
import Link from 'next/link';

const ANALYSIS_CHECKS = [
  { icon: FileSearch, text: 'Duplicate charges and unbundling violations' },
  { icon: ShieldCheck, text: 'Balance billing violations under the No Surprises Act' },
  { icon: Sparkles, text: 'Medical necessity denials that may be overturned' },
  { icon: AlertCircle, text: 'Out-of-network processing errors' },
];

function Step({ n, label, state }: { n: number; label: string; state: 'done' | 'active' | 'todo' }) {
  return (
    <div className="flex items-center gap-2.5">
      <div
        className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition-colors ${
          state === 'done'
            ? 'bg-emerald-500 text-white'
            : state === 'active'
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-muted-foreground'
        }`}
      >
        {state === 'done' ? <CheckCircle2 className="h-4 w-4" /> : n}
      </div>
      <span
        className={`text-sm font-medium ${
          state === 'todo' ? 'text-muted-foreground' : 'text-foreground'
        }`}
      >
        {label}
      </span>
    </div>
  );
}

export default function UploadPage() {
  const router = useRouter();
  const [uploadedCaseId, setUploadedCaseId] = useState<string | null>(null);
  const [uploadedFilename, setUploadedFilename] = useState<string | null>(null);

  const uploadMutation = useUploadDocument();
  const processMutation = useProcessCase();

  const handleFileSelect = async (file: File) => {
    setUploadedCaseId(null);
    setUploadedFilename(file.name);

    try {
      const result = await uploadMutation.mutateAsync(file);
      setUploadedCaseId(result.case_id);
    } catch {
      // Error is surfaced via uploadMutation.isError alert UI.
    }
  };

  const handleProcess = async () => {
    if (!uploadedCaseId) return;

    try {
      await processMutation.mutateAsync(uploadedCaseId);
      router.push(`/cases/${uploadedCaseId}`);
    } catch {
      // Error is surfaced via processMutation.isError alert UI.
    }
  };

  const isUploading = uploadMutation.isPending;
  const isProcessing = processMutation.isPending;

  return (
    <div className="container max-w-3xl mx-auto py-10 px-4">
      <Link href="/cases">
        <Button variant="ghost" size="sm" className="mb-6 -ml-2 text-muted-foreground">
          <ArrowLeft className="h-4 w-4 mr-1.5" />
          Back to Dashboard
        </Button>
      </Link>

      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight mb-2">Start a New Case</h1>
        <p className="text-muted-foreground">
          Upload your EOB, denial letter, or itemized bill. We&apos;ll extract the details and build your risk report.
        </p>
      </div>

      {/* Stepper */}
      <div className="flex items-center gap-4 sm:gap-8 mb-8 flex-wrap">
        <Step n={1} label="Upload document" state={uploadedCaseId ? 'done' : 'active'} />
        <div className="hidden sm:block h-px flex-1 bg-border" />
        <Step
          n={2}
          label="Run analysis"
          state={isProcessing ? 'active' : uploadedCaseId ? 'active' : 'todo'}
        />
        <div className="hidden sm:block h-px flex-1 bg-border" />
        <Step n={3} label="Review report" state="todo" />
      </div>

      <div className="space-y-5">
        <FileUploader onFileSelect={handleFileSelect} isUploading={isUploading} />

        {uploadMutation.isError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Upload failed: {getApiErrorMessage(uploadMutation.error)}
            </AlertDescription>
          </Alert>
        )}

        {uploadMutation.isSuccess && uploadedCaseId && (
          <Alert className="border-emerald-300 bg-emerald-50">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <AlertDescription className="text-emerald-900">
              <strong>{uploadedFilename ?? 'File'} uploaded.</strong>{' '}
              Ready to analyze — this usually takes 15–60 seconds.
            </AlertDescription>
          </Alert>
        )}

        {uploadedCaseId && (
          <div className="flex gap-3 flex-col sm:flex-row">
            <Button
              onClick={handleProcess}
              disabled={isProcessing}
              size="lg"
              className="flex-1 h-12 text-base shadow-sm"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Analyzing document...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Start Analysis
                </>
              )}
            </Button>

            <Button
              variant="outline"
              size="lg"
              className="h-12"
              disabled={isProcessing}
              onClick={() => {
                setUploadedCaseId(null);
                setUploadedFilename(null);
                uploadMutation.reset();
              }}
            >
              <FileUp className="h-4 w-4 mr-2" />
              Upload Another
            </Button>
          </div>
        )}

        {processMutation.isError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Processing failed: {getApiErrorMessage(processMutation.error)}
            </AlertDescription>
          </Alert>
        )}

        {/* Info card */}
        <div className="mt-10 p-6 bg-muted/40 rounded-xl border">
          <h3 className="font-semibold mb-4">What we analyze</h3>
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm text-muted-foreground">
            {ANALYSIS_CHECKS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-start gap-2.5">
                <Icon className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                <span>{text}</span>
              </li>
            ))}
          </ul>
          <p className="text-xs text-muted-foreground mt-5 pt-4 border-t">
            Accepted formats: <strong>PDF, TXT, PNG, JPG</strong> (max 10MB). Scanned documents are read with OCR automatically.
          </p>
        </div>
      </div>
    </div>
  );
}
