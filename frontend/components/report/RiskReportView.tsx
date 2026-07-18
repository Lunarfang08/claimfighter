'use client';

import { DollarSign, TrendingUp, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { FindingCard } from './FindingCard';
import type { RiskReport } from '@/lib/types';

interface RiskReportViewProps {
  report: RiskReport;
}

export function RiskReportView({ report }: RiskReportViewProps) {
  const appealLikelihoodColor: Record<string, string> = {
    high: 'bg-green-100 text-green-800 border-green-300',
    medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    low: 'bg-red-100 text-red-800 border-red-300',
    speculative: 'bg-gray-100 text-gray-700 border-gray-300',
  };

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total Disputed */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Disputed</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              ${parseFloat(report.total_disputed_amount).toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Out of ${parseFloat(report.total_billed_amount).toLocaleString('en-US', {
                minimumFractionDigits: 2,
              })} billed
            </p>
          </CardContent>
        </Card>

        {/* Issues Found */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Issues Found</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{report.findings.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {report.findings.length === 0
                ? 'No obvious errors detected'
                : 'Potential billing errors'}
            </p>
          </CardContent>
        </Card>

        {/* Appeal Likelihood */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Appeal Likelihood</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <Badge
              variant="outline"
              className={`text-sm font-bold ${
                appealLikelihoodColor[report.appeal_likelihood]
              }`}
            >
              {report.appeal_likelihood.toUpperCase()}
            </Badge>
            <p className="text-xs text-muted-foreground mt-2">
              {report.appeal_likelihood === 'high' &&
                'Strong case for appeal'}
              {report.appeal_likelihood === 'medium' &&
                'Moderate appeal potential'}
              {report.appeal_likelihood === 'low' &&
                'Limited appeal grounds'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Case Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Case Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">{report.case_summary}</p>
        </CardContent>
      </Card>

      {/* Findings */}
      {report.findings.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-2xl font-bold">Detailed Findings</h2>
          {report.findings.map((finding, index) => (
            <FindingCard key={index} finding={finding} index={index} />
          ))}
        </div>
      )}

      {/* Next Steps */}
      {report.next_steps.length > 0 && (
        <Card className="border-primary/50 bg-primary/5">
          <CardHeader>
            <CardTitle className="text-primary">Recommended Next Steps</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="space-y-3">
              {report.next_steps.map((step, index) => (
                <li key={index} className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-bold">
                    {index + 1}
                  </span>
                  <span className="flex-1 pt-0.5">{step}</span>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
