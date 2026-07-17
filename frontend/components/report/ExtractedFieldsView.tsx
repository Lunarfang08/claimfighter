'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { ExtractedFields } from '@/lib/types';

interface ExtractedFieldsViewProps {
  fields: ExtractedFields;
}

function FieldRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-1 py-3 border-b last:border-0">
      <span className="text-sm text-muted-foreground sm:w-48 flex-shrink-0">{label}</span>
      <span className="text-sm font-medium">{value ?? <span className="text-muted-foreground italic">Not found</span>}</span>
    </div>
  );
}

export function ExtractedFieldsView({ fields }: ExtractedFieldsViewProps) {
  return (
    <div className="space-y-4">
      {/* Document Info */}
      <Card>
        <CardHeader>
          <CardTitle>Document Information</CardTitle>
        </CardHeader>
        <CardContent>
          <FieldRow label="Document Type" value={
            <Badge variant="outline">
              {fields.document_type.replace(/_/g, ' ').toUpperCase()}
            </Badge>
          } />
          <FieldRow label="Patient Name"     value={fields.patient_name} />
          <FieldRow label="Insurer Name"     value={fields.insurer_name} />
          <FieldRow label="Policy Number"    value={fields.policy_number} />
          <FieldRow label="Claim Number"     value={fields.claim_number} />
          <FieldRow label="Date of Service"  value={fields.service_date} />
        </CardContent>
      </Card>

      {/* Medical Codes */}
      <Card>
        <CardHeader>
          <CardTitle>Medical Codes</CardTitle>
        </CardHeader>
        <CardContent>
          <FieldRow
            label="CPT Codes"
            value={
              fields.cpt_codes?.length ? (
                <div className="flex flex-wrap gap-1">
                  {fields.cpt_codes.map((code) => (
                    <Badge key={code} variant="secondary">{code}</Badge>
                  ))}
                </div>
              ) : null
            }
          />
          <FieldRow
            label="ICD Codes"
            value={
              fields.icd_codes?.length ? (
                <div className="flex flex-wrap gap-1">
                  {fields.icd_codes.map((code) => (
                    <Badge key={code} variant="secondary">{code}</Badge>
                  ))}
                </div>
              ) : null
            }
          />
        </CardContent>
      </Card>

      {/* Financial Details */}
      <Card>
        <CardHeader>
          <CardTitle>Financial Details</CardTitle>
        </CardHeader>
        <CardContent>
          <FieldRow label="Amount Billed"
            value={fields.billed_amount
              ? `$${parseFloat(fields.billed_amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}`
              : null}
          />
          <FieldRow label="Allowed Amount"
            value={fields.allowed_amount
              ? `$${parseFloat(fields.allowed_amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}`
              : null}
          />
          <FieldRow label="Patient Responsibility"
            value={fields.patient_responsibility
              ? `$${parseFloat(fields.patient_responsibility).toLocaleString('en-US', { minimumFractionDigits: 2 })}`
              : null}
          />
          <FieldRow label="Network Status"
            value={
              fields.in_network === null ? null :
              fields.in_network ? (
                <Badge className="bg-green-100 text-green-800 border-green-300">In-Network</Badge>
              ) : (
                <Badge className="bg-red-100 text-red-800 border-red-300">Out-of-Network</Badge>
              )
            }
          />
        </CardContent>
      </Card>

      {/* Denial Info */}
      <Card>
        <CardHeader>
          <CardTitle>Denial Information</CardTitle>
        </CardHeader>
        <CardContent>
          <FieldRow label="Denial Code"   value={fields.denial_reason_code
            ? <Badge variant="destructive">{fields.denial_reason_code}</Badge>
            : null}
          />
          <FieldRow label="Denial Reason" value={fields.denial_reason_text} />
        </CardContent>
      </Card>
    </div>
  );
}
