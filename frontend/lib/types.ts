/**
 * TypeScript type definitions matching the backend API responses
 */

export type CaseStatus =
  | 'uploaded'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'drafted'
  | 'approved'
  | 'sent'
  | 'awaiting_response'
  | 'escalated'
  | 'resolved';

export type ConfidenceLevel = 'high' | 'medium' | 'low';

export type DocumentType = 'eob' | 'denial_letter' | 'itemized_bill';

export interface ProcessingStep {
  step: string;
  status: 'completed' | 'failed' | 'in_progress';
  timestamp: string;
  details?: string;
}

export interface ExtractedFields {
  document_type: DocumentType;
  patient_name: string | null;
  insurer_name: string | null;
  policy_number: string | null;
  claim_number: string | null;
  service_date: string | null;
  cpt_codes: string[];
  icd_codes: string[];
  billed_amount: string | null;
  allowed_amount: string | null;
  patient_responsibility: string | null;
  denial_reason_code: string | null;
  denial_reason_text: string | null;
  in_network: boolean | null;
}

export interface Finding {
  error_type: string;
  confidence: ConfidenceLevel;
  description: string;
  evidence: string[];
  legal_citation: string;
  estimated_impact: string | null;
  recommendation: string;
}

export interface RiskReport {
  case_summary: string;
  findings: Finding[];
  total_disputed_amount: string;
  total_billed_amount: string;
  appeal_likelihood: ConfidenceLevel;
  next_steps: string[];
}

export type LetterVersionStatus = 'draft' | 'approved' | 'sent' | 'escalated';

export interface AppealLetterVersion {
  version_id: string;
  case_id: string;
  round: number;
  status: LetterVersionStatus;
  letter_text: string;
  legal_citations: string[];
  policy_references: string[];
  supporting_document_checklist: string[];
  created_at: string;
  approved_at?: string | null;
  sent_at?: string | null;
  escalated_at?: string | null;
  metadata: Record<string, unknown>;
}

export interface FollowUpState {
  round: number;
  round_1_sent_at?: string;
  round_1_response_deadline?: string;
  round_1_response_received_at?: string | null;
  escalation_ready?: boolean;
  [key: string]: unknown;
}

export interface Case {
  case_id: string;
  filename: string;
  file_path: string;
  file_type: string;
  status: CaseStatus;
  created_at: string;
  updated_at: string;
  extracted_fields: ExtractedFields | null;
  risk_report: RiskReport | null;
  processing_steps: ProcessingStep[];
  error?: string;
  appeal_letter_versions?: AppealLetterVersion[];
  current_appeal_letter_version_id?: string;
  follow_up?: FollowUpState;
}

export interface UploadResponse {
  case_id: string;
  filename: string;
  status: CaseStatus;
  message: string;
}

export interface ProcessResponse {
  message: string;
  case_id: string;
  findings_count?: number;
  total_disputed?: string;
}

export interface CasesListResponse {
  cases: Case[];
  total: number;
}
