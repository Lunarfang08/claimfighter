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

export function ProcessingStatus({ steps, currentStatus }: ProcessingStatusProps) {
  const knownStepKeys = new Set(Object.keys(STEP_LABELS));
  const completedSteps = steps.filter((s) => s.status === 'completed' && knownStepKeys.has(s.step)).length;
  const totalSteps = Object.keys(STEP_LABELS).length - 1; // Exclude 'error'
  const progress = (completedSteps / totalSteps) * 100;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {currentStatus === 'processing' && (
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
          )}
          {currentStatus === 'completed' && (
            <CheckCircle2 className="h-5 w-5 text-green-600" />
          )}
          {currentStatus === 'failed' && (
            <XCircle className="h-5 w-5 text-destructive" />
          )}
          <span>
            {currentStatus === 'processing' && 'Processing Document...'}
            {currentStatus === 'completed' && 'Processing Complete'}
            {currentStatus === 'failed' && 'Processing Failed'}
            {currentStatus === 'uploaded' && 'Ready to Process'}
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
