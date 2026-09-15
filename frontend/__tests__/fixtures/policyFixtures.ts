import { AskResponse, CitationSource, HealthResponse } from '@/types/api';

export const mockHealthResponse: HealthResponse = {
  status: 'healthy',
  version: '1.0.0',
};

export const mockCitation1: CitationSource = {
  rank: 1,
  title: 'Travel Policy 2024',
  source_file: 'data/policies/travel_policy.md',
  chunk_uid: 'travel_meal_allowance_chunk_1',
  rerank_score: 0.942,
  snippet: 'The standard domestic meal per diem allowance is $75 per day across all employee tiers.',
};

export const mockCitation2: CitationSource = {
  rank: 2,
  title: 'Expense Reimbursement Guidelines',
  source_file: 'data/policies/expense_policy.md',
  chunk_uid: 'expense_reimbursement_chunk_3',
  rerank_score: 0.884,
  snippet: 'Receipts must be submitted within 30 days of expense incurring for all meals and travel.',
};

export const mockAskSuccessResponse: AskResponse = {
  question: 'What is the meal allowance for domestic travel?',
  answer: 'The standard domestic meal per diem allowance is $75 per day for all employees.',
  is_refusal: false,
  sources: [mockCitation1, mockCitation2],
};

export const mockAskRefusalResponse: AskResponse = {
  question: 'What is the stock option vesting schedule for consultants?',
  answer: 'I cannot find information regarding stock option vesting for external consultants in the company policy documents.',
  is_refusal: true,
  sources: [],
};
