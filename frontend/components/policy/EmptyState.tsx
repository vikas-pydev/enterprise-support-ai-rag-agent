'use client';

import React from 'react';
import { BookOpen, Sparkles, Plane, PiggyBank, Clock, HeartHandshake, ArrowUpRight } from 'lucide-react';

interface EmptyStateProps {
  onSelectQuestion: (question: string) => void;
  disabled?: boolean;
}

export function EmptyState({ onSelectQuestion, disabled = false }: EmptyStateProps) {
  const exampleQuestions = [
    {
      icon: <Plane className="w-4 h-4 text-[#368F88] dark:text-[#A9DED5]" />,
      pastel: 'bg-[#E5F5F1] dark:bg-[#1A2D2A] border-[#C7E9E2] dark:border-[#244742]',
      category: 'Travel Policy',
      question: 'What is the meal per diem allowance for domestic travel?',
    },
    {
      icon: <PiggyBank className="w-4 h-4 text-[#2F855A] dark:text-[#34D399]" />,
      pastel: 'bg-[#CFE5D6] dark:bg-[#2C3B32] border-[#B7D9C2] dark:border-[#3A4D42]',
      category: 'Benefits & 401(k)',
      question: 'How much does the company match 401(k) contributions?',
    },
    {
      icon: <Clock className="w-4 h-4 text-[#B45309] dark:text-[#FBBF24]" />,
      pastel: 'bg-[#FEF3C7] dark:bg-[#393425] border-[#FDE68A] dark:border-[#4A462B]',
      category: 'Remote Work',
      question: 'What are the core collaboration hours for remote employees?',
    },
    {
      icon: <HeartHandshake className="w-4 h-4 text-[#9B1C1C] dark:text-[#F87171]" />,
      pastel: 'bg-[#FDE8E8] dark:bg-[#3D2525] border-[#FBD5D5] dark:border-[#522828]',
      category: 'Pet Insurance',
      question: 'What is the company pet insurance reimbursement policy?',
    },
  ];

  return (
    <div className="flex flex-col items-center justify-center py-6 sm:py-10 px-4 max-w-3xl mx-auto text-center select-none">
      {/* Icon Badge */}
      <div className="w-11 h-11 rounded-2xl bg-[#E5F5F1] dark:bg-[#1A2D2A] border border-[#C7E9E2] dark:border-[#244742] flex items-center justify-center text-[#368F88] dark:text-[#A9DED5] mb-3 shadow-[0_1px_2px_rgba(38,49,66,0.03)]">
        <BookOpen className="w-5 h-5" />
      </div>

      {/* Main Title & Subtitle */}
      <h2 className="text-lg sm:text-xl font-semibold text-[#263142] dark:text-[#EBEFF5] tracking-tight">
        Ask about company policies
      </h2>
      <p className="text-xs sm:text-sm text-[#697582] dark:text-[#9CA6B5] mt-1.5 max-w-xl leading-relaxed font-normal">
        Answers are synthesized strictly from indexed enterprise policy documents using hybrid semantic search and cross-encoder reranking, complete with verifiable source citations and refusal safeguards.
      </p>

      {/* Suggested Questions Grid */}
      <div className="w-full mt-6">
        <div className="flex items-center justify-center gap-1.5 mb-3 text-[11px] font-semibold uppercase tracking-wider text-[#9299A3] dark:text-[#6E7887]">
          <Sparkles className="w-3.5 h-3.5 text-[#368F88] dark:text-[#A9DED5]" />
          <span>Explore Verified Policy Inquiries</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-left">
          {exampleQuestions.map((item, idx) => (
            <button
              key={idx}
              type="button"
              disabled={disabled}
              onClick={() => onSelectQuestion(item.question)}
              className="group relative p-3.5 rounded-xl border border-[#E9E5DF] dark:border-[#2F3540] bg-[#FFFEFC] dark:bg-[#21252D] hover:bg-[#F8F6F2] dark:hover:bg-[#282D37] hover:border-[#A9DED5] dark:hover:border-[#368F88] transition-colors text-left disabled:opacity-50 disabled:pointer-events-none cursor-pointer flex flex-col justify-between shadow-[0_1px_2px_rgba(38,49,66,0.02)]"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-1.5">
                    <div className={`p-1 rounded-lg border ${item.pastel}`}>
                      {item.icon}
                    </div>
                    <span className="text-[10px] font-semibold text-[#697582] dark:text-[#9CA6B5]">
                      {item.category}
                    </span>
                  </div>
                  <ArrowUpRight className="w-3.5 h-3.5 text-[#9299A3] group-hover:text-[#368F88] dark:group-hover:text-[#A9DED5] group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                </div>
                <p className="text-xs font-semibold text-[#263142] dark:text-[#EBEFF5] group-hover:text-[#368F88] dark:group-hover:text-[#A9DED5] transition-colors leading-relaxed">
                  &ldquo;{item.question}&rdquo;
                </p>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
