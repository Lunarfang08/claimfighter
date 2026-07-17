'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { FileUploader } from '@/components/upload/FileUploader';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { CheckCircle2, AlertCircle, ArrowLeft } from 'lucide-react';
import { useUploadDocument, useProcessCase } from '@/hooks/useCases';
import { getApiErrorMessage } from '@/lib/api';
import Link from 'next/link';

export default function UploadPage() {
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadedCaseId, setUploadedCaseId] = useState<string | null>(null);

  const uploadMutation = useUploadDocument();
  const processMutation = useProcessCase();

  const handleFileSelect = async (file: File) => {
    setSelectedFile(file);
    setUploadedCaseId(null);

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
      // Navigate to the case detail page
      router.push(`/cases/${uploadedCaseId}`);
    } catch {
      // Error is surfaced via processMutation.isError alert UI.
    }
  };

  const isUploading = uploadMutation.isPending;
  const isProcessing = processMutation.isPending;

  return (
    <div className="container max-w-4xl mx-auto py-12 px-4">
      <div className="mb-8">
        <Link href="/cases">
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Cases
          </Button>
        </Link>
        
        <h1 className="text-4xl font-bold mb-2">Upload Medical Document</h1>
        <p className="text-muted-foreground">
          Upload your EOB (Explanation of Benefits), denial letter, or itemized bill to begin analysis.
        </p>
      </div>

      <div className="space-y-6">
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
          <Alert className="border-green-600 bg-green-50">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-900">
              <strong>File uploaded successfully!</strong>
              <br />
              <span className="text-sm">
                Case ID: {uploadedCaseId}
              </span>
            </AlertDescription>
          </Alert>
        )}

        {uploadedCaseId && (
          <div className="flex gap-4">
            <Button
              onClick={handleProcess}
              disabled={isProcessing}
              size="lg"
              className="flex-1"
            >
              {isProcessing ? 'Processing...' : 'Start Analysis'}
            </Button>
            
            <Button
              variant="outline"
              size="lg"
              onClick={() => {
                setSelectedFile(null);
                setUploadedCaseId(null);
                uploadMutation.reset();
              }}
            >
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

        {/* Info Card */}
        <div className="mt-12 p-6 bg-muted/50 rounded-lg border">
          <h3 className="font-semibold mb-3">What We Analyze</h3>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li className="flex items-start gap-2">
              <span className="text-primary mt-1">•</span>
              <span>Duplicate charges and unbundling violations</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary mt-1">•</span>
              <span>Balance billing violations under the No Surprises Act</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary mt-1">•</span>
              <span>Medical necessity denials that may be overturned</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary mt-1">•</span>
              <span>Out-of-network processing errors</span>
            </li>
          </ul>
          <p className="text-xs text-muted-foreground mt-4">
            <strong>Tip:</strong> Upload receipts, EOBs, or denial letters as TXT, PDF, or photos (PNG/JPG).
          </p>
        </div>
      </div>
    </div>
  );
}
