import Link from 'next/link';
import { Stethoscope } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function Navbar() {
  return (
    <header className="border-b bg-background/95 backdrop-blur sticky top-0 z-50">
      <div className="container max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 font-bold text-xl hover:opacity-80 transition-opacity">
          <Stethoscope className="h-6 w-6 text-primary" />
          <span>ClaimFighter</span>
        </Link>

        {/* Nav links */}
        <nav className="flex items-center gap-2">
          <Link href="/cases">
            <Button variant="ghost" size="sm">Dashboard</Button>
          </Link>
          <Link href="/upload">
            <Button size="sm">New Case</Button>
          </Link>
        </nav>
      </div>
    </header>
  );
}
