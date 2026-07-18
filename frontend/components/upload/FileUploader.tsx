'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import type { FileRejection } from 'react-dropzone';
import { Upload, FileText, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface FileUploaderProps {
  onFileSelect: (file: File) => void;
  isUploading?: boolean;
}

export function FileUploader({ onFileSelect, isUploading = false }: FileUploaderProps) {
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
      setError(null);

      if (rejectedFiles.length > 0) {
        const rejection = rejectedFiles[0];
        if (rejection.errors[0]?.code === 'file-too-large') {
          setError('File is too large. Maximum size is 10MB.');
        } else if (rejection.errors[0]?.code === 'file-invalid-type') {
          setError('Invalid file type. Please upload PDF, TXT, PNG, or JPG files.');
        } else {
          setError('File upload failed. Please try again.');
        }
        return;
      }

      if (acceptedFiles.length > 0) {
        onFileSelect(acceptedFiles[0]);
      }
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ['.txt'],
      'application/pdf': ['.pdf'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024, // 10MB
    disabled: isUploading,
  });

  return (
    <div className="w-full">
      <Card
        {...getRootProps()}
        className={`
          border-2 border-dashed p-10 sm:p-14 text-center cursor-pointer transition-all duration-200 rounded-xl
          ${isDragActive ? 'border-primary bg-primary/5 scale-[1.01] shadow-lg shadow-primary/10' : 'border-muted-foreground/25 bg-muted/20'}
          ${isUploading ? 'opacity-50 cursor-not-allowed' : 'hover:border-primary/60 hover:bg-primary/5'}
        `}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center gap-4">
          {isDragActive ? (
            <>
              <div className="p-4 rounded-2xl bg-primary/10">
                <Upload className="h-10 w-10 text-primary" />
              </div>
              <p className="text-lg font-medium">Drop the file here...</p>
            </>
          ) : (
            <>
              <div className="p-4 rounded-2xl bg-primary/10">
                <FileText className="h-10 w-10 text-primary" />
              </div>
              <div>
                <p className="text-lg font-medium mb-1.5">
                  {isUploading ? 'Uploading...' : 'Drop your document here, or click to browse'}
                </p>
                <p className="text-sm text-muted-foreground">
                  EOB · Denial Letter · Itemized Bill
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  PDF, TXT, PNG, or JPG — up to 10MB
                </p>
              </div>
              {!isUploading && (
                <Button type="button" variant="outline" className="mt-1 bg-background">
                  Select File
                </Button>
              )}
            </>
          )}
        </div>
      </Card>

      {error && (
        <Alert variant="destructive" className="mt-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}
