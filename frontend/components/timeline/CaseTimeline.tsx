'use client';

import { useCaseTimeline } from '@/hooks/useCases';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2 } from 'lucide-react';

const EVENT_CONFIG: Record<string, { color: string; dotColor: string; label: string }> = {
  case_created:              { color: 'bg-blue-50 border-blue-200',     dotColor: 'bg-blue-400',    label: 'Created' },
  processing_completed:      { color: 'bg-green-50 border-green-200',   dotColor: 'bg-green-500',   label: 'Processed' },
  pipeline_failed:           { color: 'bg-red-50 border-red-200',       dotColor: 'bg-red-500',     label: 'Failed' },
  letter_approved:           { color: 'bg-purple-50 border-purple-200', dotColor: 'bg-purple-500',  label: 'Approved' },
  letter_sent:               { color: 'bg-teal-50 border-teal-200',     dotColor: 'bg-teal-500',    label: 'Sent' },
  insurer_response_received: { color: 'bg-orange-50 border-orange-200', dotColor: 'bg-orange-500',  label: 'Response' },
  deadline_exceeded:         { color: 'bg-red-50 border-red-200',       dotColor: 'bg-red-600',     label: 'Deadline' },
  manual_escalation:         { color: 'bg-red-50 border-red-200',       dotColor: 'bg-red-600',     label: 'Escalated' },
  escalation_triggered:      { color: 'bg-red-50 border-red-200',       dotColor: 'bg-red-600',     label: 'Escalated' },
  case_resolved:             { color: 'bg-emerald-50 border-emerald-200',dotColor: 'bg-emerald-500',label: 'Resolved' },
};

const DEFAULT_CONFIG = { color: 'bg-gray-50 border-gray-200', dotColor: 'bg-gray-400', label: 'Event' };

export function CaseTimeline({ caseId }: { caseId: string }) {
  const { data, isLoading } = useCaseTimeline(caseId);

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const events = data?.events ?? [];

  if (events.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4 text-center">No timeline events yet.</p>
    );
  }

  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-4 top-2 bottom-2 w-0.5 bg-border" />

      <div className="space-y-4">
        {events.map((event) => {
          const cfg = EVENT_CONFIG[event.event_type] ?? DEFAULT_CONFIG;
          return (
            <div key={event.id} className="flex gap-4 items-start pl-1">
              {/* Dot */}
              <div className={`relative z-10 mt-1.5 w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center ${cfg.dotColor} ring-2 ring-background`} />

              {/* Content */}
              <div className={`flex-1 rounded-md border p-3 text-sm ${cfg.color}`}>
                <div className="flex items-start justify-between gap-2 flex-wrap">
                  <div className="font-medium leading-tight">{event.title}</div>
                  <Badge variant="outline" className="text-xs flex-shrink-0 font-normal">
                    {cfg.label}
                  </Badge>
                </div>
                {event.description && (
                  <p className="text-muted-foreground mt-1 text-xs leading-relaxed">
                    {event.description}
                  </p>
                )}
                <p className="text-muted-foreground mt-1 text-xs">
                  {new Date(event.occurred_at).toLocaleString('en-US', {
                    month: 'short', day: 'numeric', year: 'numeric',
                    hour: '2-digit', minute: '2-digit',
                  })}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
