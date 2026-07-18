'use client';

import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import type { ProcessingStep } from '@/lib/types';

interface ProcessingStatusProps {
  steps: ProcessingStep[];
  currentStatus: string;
}

const STEP_LABELS: Record<string, string> = {
  upload: 'Document Uploaded',
  load_text: 'Loading Document Text',
  initialize_llm: 'Initializing AI Model',
  classify_document: 'Classifying Document Type',
  extract_fields: 'Extracting Structured Data',
  rule_engine: 'Running Error Detection',
  risk_report: 'Generating Risk Report',
  draft_appeal_letter: 'Drafting Appeal Letter',
  approve_appeal_letter: 'Approving Appeal Letter',
  send_appeal_letter: 'Sending Appeal Letter',
  insurer_response_received: 'Insurer Response Received',
  escalation_deadline_reached: 'Escalation Packet Generated',
  error: 'Processing Failed',
};

const CORE_PIPELINE_STEPS = [
  'upload', 'load_text', 'initialize_llm', 'classify_document',
  'extract_fields', 'rule_engine', 'risk_report', 'draft_appeal_letter',
];

export function ProcessingStatus({ steps, currentStatus }: ProcessingStatusProps) {
  const coreSet = new Set(CORE_PIPELINE_STEPS);
  const completedSteps = steps.filter((s) => s.status === 'completed' && coreSet.has(s.step)).length;
  // Once the pipeline finishes, show a full bar regardless of which steps ran
  const progress = ['uploaded', 'processing'].includes(currentStatus)
    ? (completedSteps / CORE_PIPELINE_STEPS.length) * 100
    : 100;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {currentStatus === 'processing' ? (
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
          ) : currentStatus === 'failed' ? (
            <XCircle className="h-5 w-5 text-destructive" />
          ) : currentStatus === 'uploaded' ? (
            <Circle className="h-5 w-5 text-muted-foreground" />
          ) : (
            <CheckCircle2 className="h-5 w-5 text-green-600" />
          )}
          <span>
            {currentStatus === 'processing' ? 'Processing Document...'
              : currentStatus === 'failed' ? 'Processing Failed'
              : currentStatus === 'uploaded' ? 'Ready to Process'
              : 'Processing Complete'}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Progress value={progress} className="w-full" />
        
        <div className="space-y-3">
          {steps.map((step, index) => (
            <div key={index} className="flex items-start gap-3">
              <div className="mt-0.5">
                {step.status === 'completed' ? (
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                ) : step.status === 'failed' ? (
                  <XCircle className="h-5 w-5 text-destructive" />
                ) : (
                  <Circle className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">
                  {STEP_LABELS[step.step] || step.step}
                </p>
                {step.details && (
                  <p className="text-xs text-muted-foreground mt-1">
                    {step.details}
                  </p>
                )}
                <p className="text-xs text-muted-foreground mt-0.5">
                  {new Date(step.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
