'use client';

import { AlertTriangle, CheckCircle2, Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { Finding, ConfidenceLevel } from '@/lib/types';

interface FindingCardProps {
  finding: Finding;
  index: number;
}

const CONFIDENCE_CONFIG: Record<
  ConfidenceLevel,
  { icon: React.ElementType; color: string; bgColor: string; label: string }
> = {
  high: {
    icon: AlertTriangle,
    color: 'text-red-600',
    bgColor: 'bg-red-50 border-red-200',
    label: 'High Confidence',
  },
  medium: {
    icon: Info,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50 border-yellow-200',
    label: 'Medium Confidence',
  },
  low: {
    icon: CheckCircle2,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50 border-blue-200',
    label: 'Low Confidence',
  },
  speculative: {
    icon: Info,
    color: 'text-gray-500',
    bgColor: 'bg-gray-50 border-gray-200',
    label: 'Speculative',
  },
};

export function FindingCard({ finding, index }: FindingCardProps) {
  const config = CONFIDENCE_CONFIG[finding.confidence];
  const Icon = config.icon;

  return (
    <Card className={`${config.bgColor} border-2`}>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3 flex-1">
            <Icon className={`h-6 w-6 ${config.color} mt-0.5 flex-shrink-0`} />
            <div className="flex-1 min-w-0">
              <CardTitle className="text-lg">
                Finding #{index + 1}: {finding.error_type.replace(/_/g, ' ').toUpperCase()}
              </CardTitle>
            </div>
          </div>
          <Badge variant="outline" className={config.color}>
            {config.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Description */}
        <div>
          <h4 className="font-semibold text-sm mb-2">Description</h4>
          <p className="text-sm text-muted-foreground">{finding.description}</p>
        </div>

        {/* Evidence */}
        {finding.evidence.length > 0 && (
          <div>
            <h4 className="font-semibold text-sm mb-2">Evidence</h4>
            <ul className="space-y-1">
              {finding.evidence.map((item, idx) => (
                <li key={idx} className="text-sm text-muted-foreground flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span className="flex-1">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Legal Citation */}
        {finding.legal_citation && (
          <div className="bg-background/60 p-3 rounded-md border">
            <h4 className="font-semibold text-sm mb-1">Legal Basis</h4>
            <p className="text-xs text-muted-foreground italic">
              {finding.legal_citation}
            </p>
          </div>
        )}

        {/* Estimated Impact */}
        {finding.estimated_impact && (
          <div className="flex items-center justify-between pt-2 border-t">
            <span className="text-sm font-medium">Estimated Recovery:</span>
            <span className="text-lg font-bold text-green-600">
              ${parseFloat(finding.estimated_impact).toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </span>
          </div>
        )}

        {/* Recommendation */}
        <div className="bg-primary/5 p-3 rounded-md border border-primary/20">
          <h4 className="font-semibold text-sm mb-1 text-primary">Recommended Action</h4>
          <p className="text-sm">{finding.recommendation}</p>
        </div>
      </CardContent>
    </Card>
  );
}
