import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Upload, Shield, FileSearch, Gavel, ArrowRight, FileText,
  ScanLine, PenLine, Clock, CheckCircle2, Scale, FileDown,
} from 'lucide-react';

const FEATURES = [
  {
    icon: ScanLine,
    title: 'Any Document Format',
    description:
      'Upload EOBs, denial letters, or itemized bills as PDF, image, or text. Built-in OCR reads scanned documents automatically.',
  },
  {
    icon: FileSearch,
    title: 'AI-Powered Extraction',
    description:
      'Extracts patient info, CPT/ICD codes, denial reasons, and dollar amounts into a structured, reviewable record.',
  },
  {
    icon: Shield,
    title: 'Deterministic Error Detection',
    description:
      'Rule-based checks catch duplicate charges, unbundling violations, and No Surprises Act balance-billing errors — no hallucinations.',
  },
  {
    icon: Gavel,
    title: 'Legal-Backed Findings',
    description:
      'Every finding cites specific laws — EMTALA, the No Surprises Act, NCCI edits — with a concrete recommended action.',
  },
  {
    icon: PenLine,
    title: 'AI-Drafted Appeal Letters',
    description:
      'Generates a formal appeal letter with citations and a supporting-document checklist. Edit, approve, and download as PDF.',
  },
  {
    icon: Clock,
    title: 'Automated Follow-up Loop',
    description:
      'Tracks response deadlines, drafts Round 2 rebuttals from the insurer\u2019s reply, and prepares escalation packets when deadlines pass.',
  },
];

const WORKFLOW = [
  {
    step: '01',
    icon: Upload,
    title: 'Upload',
    description: 'Drop in your denial letter, EOB, or bill. OCR and AI extraction run in seconds.',
  },
  {
    step: '02',
    icon: FileSearch,
    title: 'Analyze',
    description: 'Get a risk report: billing errors, legal violations, disputed dollars, and appeal likelihood.',
  },
  {
    step: '03',
    icon: FileDown,
    title: 'Appeal',
    description: 'Review the AI-drafted appeal letter, make edits, approve it, and send it as a polished PDF.',
  },
  {
    step: '04',
    icon: Scale,
    title: 'Follow Up',
    description: 'The system tracks deadlines, drafts Round 2 responses, and escalates to regulators if needed.',
  },
];

const DENIAL_TYPES = [
  { code: 'CO-50', label: 'Medical Necessity' },
  { code: 'CO-16', label: 'Code Mismatch' },
  { code: 'CO-96', label: 'Out-of-Network' },
  { code: 'NSA', label: 'Balance Billing' },
  { code: 'DUP', label: 'Duplicate Charges' },
  { code: 'NCCI', label: 'Unbundling' },
];

const STATS = [
  { value: '4', label: 'Analysis stages per case' },
  { value: '6+', label: 'Error types detected' },
  { value: '2', label: 'Appeal rounds automated' },
  { value: '100%', label: 'Citations from real law' },
];

export default function HomePage() {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="relative overflow-hidden border-b">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.07] via-transparent to-accent/40 pointer-events-none" />
        <div
          className="absolute inset-0 opacity-[0.4] pointer-events-none"
          style={{
            backgroundImage:
              'radial-gradient(circle at 1px 1px, oklch(0.5 0.17 255 / 8%) 1px, transparent 0)',
            backgroundSize: '28px 28px',
          }}
        />
        <div className="container max-w-5xl mx-auto text-center relative py-24 md:py-32 px-4">
          <Badge
            variant="outline"
            className="mb-6 px-3 py-1 text-xs font-medium bg-background/80 backdrop-blur border-primary/30 text-primary"
          >
            <CheckCircle2 className="h-3 w-3 mr-1.5" />
            End-to-end appeal pipeline — analysis to escalation
          </Badge>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6 text-balance">
            Fight Your Medical Bills
            <span className="block bg-gradient-to-r from-primary to-chart-2 bg-clip-text text-transparent pb-1">
              with an AI Advocate
            </span>
          </h1>
          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
            Upload a denial letter, EOB, or itemized bill. Get a risk report with legal citations,
            an editable appeal letter, and automated deadline tracking — in seconds.
          </p>
          <div className="flex gap-3 justify-center flex-wrap">
            <Link href="/upload">
              <Button size="lg" className="text-base px-8 h-12 shadow-lg shadow-primary/20">
                Analyze a Document
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
            <Link href="/cases">
              <Button size="lg" variant="outline" className="text-base px-8 h-12 bg-background/80 backdrop-blur">
                Open Dashboard
              </Button>
            </Link>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-16 max-w-3xl mx-auto">
            {STATS.map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-3xl font-bold text-primary">{s.value}</div>
                <div className="text-xs text-muted-foreground mt-1">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Denial types marquee strip */}
      <section className="py-8 border-b bg-muted/40">
        <div className="container max-w-5xl mx-auto px-4 text-center">
          <p className="text-xs text-muted-foreground mb-4 font-semibold uppercase tracking-widest">
            Denial types we detect and dispute
          </p>
          <div className="flex gap-2.5 justify-center flex-wrap">
            {DENIAL_TYPES.map((d) => (
              <span
                key={d.code}
                className="inline-flex items-center gap-2 rounded-full border bg-background px-4 py-1.5 text-sm shadow-sm"
              >
                <span className="font-mono font-semibold text-primary text-xs">{d.code}</span>
                <span className="text-muted-foreground">{d.label}</span>
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Workflow */}
      <section className="py-20 md:py-24 px-4">
        <div className="container max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold mb-3">From denial to appeal in four steps</h2>
            <p className="text-muted-foreground max-w-xl mx-auto">
              A complete case workflow — not just analysis. ClaimFighter stays on your case until it&apos;s resolved.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {WORKFLOW.map((w, i) => {
              const Icon = w.icon;
              return (
                <div key={w.step} className="relative group">
                  <Card className="h-full border-border/70 transition-all duration-200 group-hover:border-primary/40 group-hover:shadow-lg group-hover:shadow-primary/5 group-hover:-translate-y-0.5">
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between mb-4">
                        <div className="p-2.5 rounded-xl bg-primary/10 text-primary">
                          <Icon className="h-5 w-5" />
                        </div>
                        <span className="text-3xl font-bold text-muted-foreground/20 font-mono">{w.step}</span>
                      </div>
                      <h3 className="font-semibold text-lg mb-1.5">{w.title}</h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">{w.description}</p>
                    </CardContent>
                  </Card>
                  {i < WORKFLOW.length - 1 && (
                    <ArrowRight className="hidden lg:block absolute top-1/2 -right-4 -translate-y-1/2 h-4 w-4 text-muted-foreground/40 z-10" />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 md:py-24 px-4 bg-muted/40 border-y">
        <div className="container max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold mb-3">Built for real appeals</h2>
            <p className="text-muted-foreground max-w-xl mx-auto">
              Deterministic rule checks keep findings auditable. AI makes the letters persuasive. You stay in control.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map((f) => {
              const Icon = f.icon;
              return (
                <Card
                  key={f.title}
                  className="border-border/70 bg-card hover:shadow-md hover:border-primary/30 transition-all duration-200"
                >
                  <CardContent className="pt-6">
                    <div className="p-2.5 rounded-xl bg-primary/10 text-primary w-fit mb-4">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h3 className="font-semibold mb-1.5">{f.title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">{f.description}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="py-20 md:py-28 px-4 text-center relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-t from-primary/[0.06] to-transparent pointer-events-none" />
        <div className="relative">
          <div className="inline-flex p-3 rounded-2xl bg-primary/10 text-primary mb-6">
            <FileText className="h-7 w-7" />
          </div>
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Ready to fight your claim?</h2>
          <p className="text-muted-foreground mb-8 max-w-md mx-auto">
            Upload a denial letter and see your full risk report — findings, citations, and a drafted appeal — in under a minute.
          </p>
          <Link href="/upload">
            <Button size="lg" className="text-base px-10 h-12 shadow-lg shadow-primary/20">
              Get Started Free
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </Link>
        </div>
      </section>
    </div>
  );
}
