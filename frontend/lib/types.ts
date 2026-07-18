/**
 * TypeScript type definitions — Phases 1-4
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

export type ConfidenceLevel = 'high' | 'medium' | 'low' | 'speculative';

export type DocumentType = 'eob' | 'denial_letter' | 'itemized_bill' | 'unknown';

export type LetterVersionStatus = 'draft' | 'approved' | 'sent' | 'escalated';

export type ResolutionOutcome = 'won' | 'partial' | 'lost';

// ────────────────────────────────────────────────────────────────────────────
// Processing
// ────────────────────────────────────────────────────────────────────────────

export interface ProcessingStep {
  step: string;
  status: 'completed' | 'failed' | 'in_progress';
  timestamp: string;
  details?: string;
}

// ────────────────────────────────────────────────────────────────────────────
// Extracted Fields
// ────────────────────────────────────────────────────────────────────────────

export interface ExtractedFields {
  document_type: DocumentType;
  patient_name: string | null;
  patient_id: string | null;
  insurer_name: string | null;
  provider_name: string | null;
  service_date: string | null;
  service_date_end: string | null;
  cpt_codes: string[];
  icd_codes: string[];
  billed_amount: string | null;
  allowed_amount: string | null;
  paid_amount: string | null;
  patient_responsibility: string | null;
  denial_reason_code: string | null;
  denial_reason_text: string | null;
  in_network: boolean | null;
  raw_denial_context: string | null;
}

// ────────────────────────────────────────────────────────────────────────────
// Risk Report
// ────────────────────────────────────────────────────────────────────────────

export interface Finding {
  error_type: string;
  confidence: ConfidenceLevel;
  description: string;
  evidence: string[];
  legal_citation: string | null;
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

// ────────────────────────────────────────────────────────────────────────────
// Appeal Letters (Phase 2)
// ────────────────────────────────────────────────────────────────────────────

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
  pdf_path?: string | null;
}

// ────────────────────────────────────────────────────────────────────────────
// Follow-up State (Phase 4)
// ────────────────────────────────────────────────────────────────────────────

export interface FollowUpState {
  round: number;
  agent_state: string;
  round_1_sent_at?: string | null;
  round_1_response_deadline?: string | null;
  round_1_response_received_at?: string | null;
  round_1_response_excerpt?: string | null;
  round_2_sent_at?: string | null;
  round_2_response_deadline?: string | null;
  round_2_response_received_at?: string | null;
  escalation_ready?: boolean;
  escalation_triggered_at?: string | null;
}

// ────────────────────────────────────────────────────────────────────────────
// Timeline (Phase 3)
// ────────────────────────────────────────────────────────────────────────────

export interface TimelineEvent {
  id: number;
  event_type: string;
  title: string;
  description: string | null;
  occurred_at: string;
  metadata: Record<string, unknown>;
}

// ────────────────────────────────────────────────────────────────────────────
// Case
// ────────────────────────────────────────────────────────────────────────────

export interface Resolution {
  outcome: ResolutionOutcome;
  notes: string | null;
  resolved_at: string;
}

export interface Case {
  case_id: string;
  filename: string;
  file_path: string;
  file_type: string;
  status: CaseStatus;
  created_at: string;
  updated_at: string;
  error?: string | null;
  extracted_fields: ExtractedFields | null;
  risk_report: RiskReport | null;
  processing_steps: ProcessingStep[];
  appeal_letter_versions?: AppealLetterVersion[];
  current_appeal_letter_version_id?: string | null;
  follow_up?: FollowUpState | null;
  resolution?: Resolution | null;
}

// ────────────────────────────────────────────────────────────────────────────
// API Responses
// ────────────────────────────────────────────────────────────────────────────

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
  limit: number;
  offset: number;
}

export interface AppealLetterResponse {
  case_id: string;
  current: AppealLetterVersion | null;
  versions: AppealLetterVersion[];
  follow_up: FollowUpState | null;
}

export interface TimelineResponse {
  case_id: string;
  events: TimelineEvent[];
}
