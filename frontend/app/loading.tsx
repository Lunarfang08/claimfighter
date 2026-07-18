import { Loader2 } from 'lucide-react';

export default function Loading() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] gap-3">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
      <p className="text-sm text-muted-foreground">Loading...</p>
    </div>
  );
}
