'use client';

import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] px-4 text-center">
      <div className="p-4 rounded-2xl bg-destructive/10 text-destructive mb-6">
        <AlertTriangle className="h-8 w-8" />
      </div>
      <h1 className="text-2xl font-bold mb-2">Something went wrong</h1>
      <p className="text-muted-foreground max-w-md mb-2">
        An unexpected error occurred. This is usually temporary — try again in a moment.
      </p>
      {error.digest && (
        <p className="text-xs text-muted-foreground font-mono mb-6">Error ID: {error.digest}</p>
      )}
      <div className="flex gap-3 mt-4">
        <Button onClick={reset}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Try Again
        </Button>
        <Link href="/">
          <Button variant="outline">
            <Home className="h-4 w-4 mr-2" />
            Go Home
          </Button>
        </Link>
      </div>
    </div>
  );
}
