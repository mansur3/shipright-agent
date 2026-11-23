// ── Auth ──────────────────────────────────────────────────────────────────────
export type Role =
  | "cfo"
  | "supply_chain"
  | "claims_finance"
  | "sales_rsm"
  | "cnf_agent"
  | "admin";

export interface AuthUser {
  username: string;
  role: Role;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: Role;
  username: string;
}

export interface MeResponse {
  username: string;
  role: Role;
  email: string;
  cnf_code: string | null;
}

export interface HealthResponse {
  ok: boolean;
  model_key_set: boolean;
  last_batch: string | null;
  addressable_inr: number | null;
}

// ── Dashboard / batch summary ─────────────────────────────────────────────────
export interface BatchSummary {
  run_at?: string;
  message?: string;
  total_claims?: number;
  total_sales_rows?: number;
  duplicate_groups?: number;
  duplicate_excess_inr?: number;
  zero_invoice_inr?: number;
  qty_overclaim_inr?: number;
  pending_suspicious_inr?: number;
  at_risk_30d_inr?: number;
  at_risk_60d_inr?: number;
  at_risk_90d_inr?: number;
  at_risk_180d_inr?: number;
  total_addressable_inr?: number;
  high_risk_stockists?: number;
}

// ── At-risk stock ─────────────────────────────────────────────────────────────
export interface AtRiskBatch {
  cnf_code: string;
  cnf_city?: string;
  sku_code: string;
  product: string;
  batch_no: string;
  expiry_date: string;
  days_to_expiry: number;
  qty_packs: number;
  pts_inr?: number;
  value_inr: number;
  avg_monthly_outward?: number;
  sellable_before_expiry?: number;
  recommend_redistribute: boolean;
  source?: string;
}

export interface AtRiskResponse {
  batches: AtRiskBatch[];
  total_batches: number;
  total_value_inr: number;
  by_therapy_area?: Record<string, number>;
  run_at?: string;
  source?: string;
}

// ── Fill rate ──────────────────────────────────────────────────────────────────
export interface FillRateRow {
  cnf_code: string;
  ordered_qty: number;
  invoiced_qty: number;
  fill_rate_pct: number;
  unfilled_qty: number;
}

export interface FillRateResponse {
  by_cnf: FillRateRow[];
  overall_fill_rate_pct: number;
  source?: string;
}

// ── Quarter spike ──────────────────────────────────────────────────────────────
export interface QuarterSpikePhase {
  quarter: string;
  total_inr: number;
  last9d_inr: number;
  spike_pct: number;
  scheme_pct: number;
}

export interface QuarterSpikeResponse {
  found?: boolean;
  sku_code?: string;
  product?: string;
  phasing_by_quarter?: QuarterSpikePhase[];
  avg_spike_pct_last4q?: number;
  risk_level?: "LOW" | "MEDIUM" | "HIGH";
  latest_quarter?: string;
  latest_spike_pct?: number;
  projected_expiry_return_inr?: number;
  source?: string;
}

// ── Claim findings ────────────────────────────────────────────────────────────
export interface ClaimFinding {
  claim_no: string;
  stockist_code: string;
  batch_no: string;
  sku_code: string;
  claim_type: string;
  claim_date: string | null;
  claim_value_inr: number;
  status: string;
  risk_score: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH";
  signals: string[];
  has_invoice: boolean;
  invoiced_qty: number;
  claimed_qty: number;
  recommended_action: string;
}

export interface ClaimFindingsResponse {
  findings: ClaimFinding[];
  total: number;
  run_at: string;
}

// ── User-submitted claims ──────────────────────────────────────────────────────
export interface UserClaim {
  id: number;
  claim_no: string;
  submitted_by?: string;
  status: string;
  stockist_code: string;
  batch_no: string;
  sku_code: string;
  qty_claimed: number;
  claim_date: string;
  claim_type: string;
  invoice_ref?: string;
  risk_score: number;
  risk_flags: string[];
  claim_value_inr: number;
  recovery_amount_inr: number;
  auditor_username?: string | null;
  auditor_notes?: string | null;
  created_at: string;
  updated_at?: string;
  resolved_at?: string | null;
}

export interface MyClaimsResponse {
  claims: UserClaim[];
  total: number;
  total_claim_value_inr: number;
  total_recovery_inr: number;
}

export interface AllClaimsResponse {
  claims: UserClaim[];
  total: number;
}

export interface ReviewResponse {
  claim_no: string;
  status: string;
  reviewed_by: string;
  recovery_inr: number;
}

// ── Claims chat ──────────────────────────────────────────────────────────────────
export interface ClaimsChatResponse {
  answer: string;
  intent: string;
  claim_no: string | null;
  session_id: string;
  status_result?: {
    claims: UserClaim[];
    total: number;
    total_value_inr: number;
  } | null;
  recovery_result?: Record<string, number> | null;
}

// ── Ask AI ──────────────────────────────────────────────────────────────────────
export interface ChatEvidence {
  tool: string;
  summary: string;
}

export interface AskResponse {
  answer: string;
  evidence: ChatEvidence[];
  model_calls: number;
  usage?: { input_tokens: number; output_tokens: number; seconds: number; cost_inr_estimate: number; model: string } | null;
  flags: string[];
  blocked: boolean;
}

// ── Recovery benchmark ──────────────────────────────────────────────────────────
export interface BenchmarkResponse {
  batch_analysis: {
    duplicate_excess_inr: number;
    zero_invoice_inr: number;
    qty_overclaim_inr: number;
    at_risk_30d_inr: number;
    at_risk_60d_inr: number;
    at_risk_90d_inr: number;
    total_addressable_inr: number;
  } | null;
  user_claims: {
    total_submitted: number;
    pending: number;
    pending_value_inr: number;
    approved: number;
    approved_value_inr: number;
    rejected: number;
    rejected_value_inr: number;
    credited: number;
    credited_value_inr: number;
    recovery_from_blocks_inr: number;
    recovery_from_reviews_inr: number;
  };
  benchmark: {
    recovered_inr: number;
    recoverable_now_inr: number;
    at_risk_inr: number;
    total_addressable_inr: number;
    projected_annual_inr: number;
  };
}

// ── Admin ──────────────────────────────────────────────────────────────────────
export interface AdminUser {
  id: number;
  username: string;
  email: string;
  role: Role;
  cnf_code: string | null;
  is_active: boolean;
}

export interface AuditLogEntry {
  id: number;
  username: string;
  action: string;
  endpoint: string;
  success: boolean;
  detail: string | null;
  created_at: string;
}

export interface BatchHistoryEntry {
  id: number;
  run_at: string;
  total_addressable_inr: number;
  duplicate_groups: number;
  high_risk_stockists: number;
}

export interface RunBatchResponse {
  message: string;
  run_at: string;
  total_addressable_inr: number;
  findings: number;
  stock_alerts: number;
}
