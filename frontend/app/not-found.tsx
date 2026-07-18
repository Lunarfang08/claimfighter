import Link from 'next/link';
import { FileQuestion, Home, LayoutDashboard } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] px-4 text-center">
      <div className="p-4 rounded-2xl bg-primary/10 text-primary mb-6">
        <FileQuestion className="h-8 w-8" />
      </div>
      <h1 className="text-2xl font-bold mb-2">Page not found</h1>
      <p className="text-muted-foreground max-w-md mb-8">
        The page you&apos;re looking for doesn&apos;t exist or may have been moved.
      </p>
      <div className="flex gap-3">
        <Link href="/">
          <Button>
            <Home className="h-4 w-4 mr-2" />
            Go Home
          </Button>
        </Link>
        <Link href="/cases">
          <Button variant="outline">
            <LayoutDashboard className="h-4 w-4 mr-2" />
            Dashboard
          </Button>
        </Link>
      </div>
    </div>
  );
}
