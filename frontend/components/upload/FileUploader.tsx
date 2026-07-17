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
          border-2 border-dashed p-12 text-center cursor-pointer transition-colors
          ${isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'}
          ${isUploading ? 'opacity-50 cursor-not-allowed' : 'hover:border-primary hover:bg-primary/5'}
        `}
      >
        <input {...getInputProps()} />
        
        <div className="flex flex-col items-center gap-4">
          {isDragActive ? (
            <>
              <Upload className="h-12 w-12 text-primary" />
              <p className="text-lg font-medium">Drop the file here...</p>
            </>
          ) : (
            <>
              <FileText className="h-12 w-12 text-muted-foreground" />
              <div>
                <p className="text-lg font-medium mb-2">
                  {isUploading ? 'Uploading...' : 'Drop your document here, or click to select'}
                </p>
                <p className="text-sm text-muted-foreground">
                  Supports: EOB, Denial Letter, Itemized Bill
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Accepted formats: TXT, PDF, PNG, JPG (max 10MB)
                </p>
              </div>
              {!isUploading && (
                <Button type="button" variant="outline" className="mt-2">
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
