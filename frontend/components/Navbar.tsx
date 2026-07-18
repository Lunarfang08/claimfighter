'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ShieldPlus, LayoutDashboard, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export function Navbar() {
  const pathname = usePathname();
  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <header className="border-b bg-background/80 backdrop-blur-md sticky top-0 z-50">
      <div className="container max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2.5 font-bold text-lg hover:opacity-80 transition-opacity"
        >
          <div className="p-1.5 rounded-lg bg-primary text-primary-foreground">
            <ShieldPlus className="h-4.5 w-4.5" />
          </div>
          <span className="tracking-tight">
            Claim<span className="text-primary">Fighter</span>
          </span>
        </Link>

        {/* Nav links */}
        <nav className="flex items-center gap-1.5">
          <Link href="/cases">
            <Button
              variant="ghost"
              size="sm"
              className={cn(
                'gap-1.5',
                isActive('/cases') && 'bg-accent text-accent-foreground'
              )}
            >
              <LayoutDashboard className="h-4 w-4" />
              <span className="hidden sm:inline">Dashboard</span>
            </Button>
          </Link>
          <Link href="/upload">
            <Button size="sm" className="gap-1.5 shadow-sm">
              <Plus className="h-4 w-4" />
              New Case
            </Button>
          </Link>
        </nav>
      </div>
    </header>
  );
}
