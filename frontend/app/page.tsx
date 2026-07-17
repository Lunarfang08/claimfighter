import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Upload, Shield, FileSearch, Gavel,
  ArrowRight, CheckCircle2
} from 'lucide-react';

const FEATURES = [
  {
    icon: Upload,
    title: 'Upload Any Document',
    description: 'Submit EOBs, denial letters, or itemized bills in TXT format (PDF and image support coming in Phase 2).',
  },
  {
    icon: FileSearch,
    title: 'AI-Powered Extraction',
    description: 'Automatically extracts patient info, CPT/ICD codes, denial reasons, and dollar amounts.',
  },
  {
    icon: Shield,
    title: 'Rule-Based Error Detection',
    description: 'Deterministic checks for duplicate charges, unbundling violations, and No Surprises Act violations.',
  },
  {
    icon: Gavel,
    title: 'Legal-Backed Findings',
    description: 'Every finding cites specific laws (EMTALA, No Surprises Act, NCCI edits) with actionable recommendations.',
  },
];

const DENIAL_TYPES = [
  { code: 'CO-50', label: 'Medical Necessity', color: 'bg-red-100 text-red-800' },
  { code: 'CO-16', label: 'Code Mismatch', color: 'bg-orange-100 text-orange-800' },
  { code: 'CO-96', label: 'Out-of-Network', color: 'bg-yellow-100 text-yellow-800' },
  { code: 'NSA',   label: 'Balance Billing', color: 'bg-blue-100 text-blue-800' },
];

export default function HomePage() {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="bg-gradient-to-b from-primary/10 to-background py-20 px-4">
        <div className="container max-w-4xl mx-auto text-center">
          <Badge variant="outline" className="mb-4 text-sm">
            Phase 1 — Static Analysis Pipeline
          </Badge>
          <h1 className="text-5xl font-bold tracking-tight mb-6">
            Fight Your Medical Bills with AI
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-10">
            Upload a denial letter, EOB, or itemized bill. Get a detailed risk report
            with legal citations, error findings, and step-by-step appeal guidance — in seconds.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Link href="/upload">
              <Button size="lg" className="text-base px-8">
                Analyze a Document
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
            <Link href="/cases">
              <Button size="lg" variant="outline" className="text-base px-8">
                View All Cases
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Supported denial types */}
      <section className="py-10 border-b">
        <div className="container max-w-4xl mx-auto px-4 text-center">
          <p className="text-sm text-muted-foreground mb-4 font-medium uppercase tracking-wider">
            Denial types we handle
          </p>
          <div className="flex gap-3 justify-center flex-wrap">
            {DENIAL_TYPES.map((d) => (
              <Badge key={d.code} className={`text-sm px-3 py-1 ${d.color}`}>
                {d.code} — {d.label}
              </Badge>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-4">
        <div className="container max-w-5xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {FEATURES.map((f) => {
              const Icon = f.icon;
              return (
                <Card key={f.title} className="hover:shadow-md transition-shadow">
                  <CardHeader className="flex flex-row items-center gap-4 pb-2">
                    <div className="p-2 rounded-lg bg-primary/10">
                      <Icon className="h-6 w-6 text-primary" />
                    </div>
                    <CardTitle className="text-lg">{f.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground">{f.description}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* CTA / Roadmap */}
      <section className="py-20 px-4 bg-muted/50">
        <div className="container max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-4">What&apos;s Coming Next</h2>
          <p className="text-center text-muted-foreground mb-10">
            Phase 1 is the foundation. Here&apos;s the full roadmap.
          </p>
          <div className="space-y-4">
            {[
              { phase: 'Phase 1', label: 'Static Analysis Pipeline', done: true,
                items: ['Document upload & parsing', 'Field extraction via LLM', 'Rule-based error detection', 'Risk report generation'] },
              { phase: 'Phase 2', label: 'Letter Drafting + PDF Support', done: false,
                items: ['AI-generated appeal letters', 'PDF & image upload (OCR)', 'Editable letter interface'] },
              { phase: 'Phase 3', label: 'Persistence & Case History', done: false,
                items: ['PostgreSQL case storage', 'Full case timeline', 'Search and filtering'] },
              { phase: 'Phase 4', label: 'Follow-up Loop (LangGraph)', done: false,
                items: ['Agentic state machine', 'Deadline tracking', 'Round-2 appeal drafting'] },
            ].map((p) => (
              <Card key={p.phase} className={p.done ? 'border-green-300 bg-green-50' : ''}>
                <CardContent className="pt-5 pb-4">
                  <div className="flex items-start gap-3">
                    {p.done ? (
                      <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                    ) : (
                      <div className="h-5 w-5 rounded-full border-2 border-muted-foreground/30 mt-0.5 flex-shrink-0" />
                    )}
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant={p.done ? 'default' : 'outline'} className="text-xs">
                          {p.phase}
                        </Badge>
                        <span className="font-semibold">{p.label}</span>
                      </div>
                      <ul className="text-sm text-muted-foreground space-y-0.5">
                        {p.items.map((item) => (
                          <li key={item}>• {item}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="py-16 px-4 text-center">
        <h2 className="text-3xl font-bold mb-4">Ready to fight your claim?</h2>
        <p className="text-muted-foreground mb-8 max-w-md mx-auto">
          Upload a sample denial letter and see your risk report in under 30 seconds.
        </p>
        <Link href="/upload">
          <Button size="lg" className="text-base px-10">
            Get Started Free
            <ArrowRight className="ml-2 h-5 w-5" />
          </Button>
        </Link>
      </section>
    </div>
  );
}
