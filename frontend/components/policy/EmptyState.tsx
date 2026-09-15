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
      icon: <Plane className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />,
      category: 'Travel Policy',
      question: 'What is the meal per diem allowance for domestic travel?',
    },
    {
      icon: <PiggyBank className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />,
      category: 'Benefits & 401(k)',
      question: 'How much does the company match 401(k) contributions?',
    },
    {
      icon: <Clock className="w-4 h-4 text-amber-600 dark:text-amber-400" />,
      category: 'Remote Work',
      question: 'What are the core collaboration hours for remote employees?',
    },
    {
      icon: <HeartHandshake className="w-4 h-4 text-rose-600 dark:text-rose-400" />,
      category: 'Pet Insurance',
      question: 'What is the company pet insurance reimbursement policy?',
    },
  ];

  return (
    <div className="flex flex-col items-center justify-center py-8 sm:py-12 px-4 max-w-3xl mx-auto text-center">
      {/* Icon Badge */}
      <div className="w-14 h-14 rounded-3xl bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/30 flex items-center justify-center text-cyan-600 dark:text-cyan-400 mb-4 shadow-lg shadow-cyan-500/10">
        <BookOpen className="w-7 h-7" />
      </div>

      {/* Main Title & Subtitle */}
      <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 dark:text-white tracking-tight">
        Ask about company policies
      </h2>
      <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 mt-2 max-w-xl leading-relaxed font-normal">
        Answers are synthesized strictly from indexed enterprise policy documents using hybrid semantic search and cross-encoder reranking, complete with verifiable source citations and refusal safeguards.
      </p>

      {/* Suggested Questions Grid */}
      <div className="w-full mt-8">
        <div className="flex items-center justify-center gap-2 mb-4 text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          <Sparkles className="w-3.5 h-3.5 text-cyan-500 dark:text-cyan-400" />
          <span>Explore Verified Policy Inquiries</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
          {exampleQuestions.map((item, idx) => (
            <button
              key={idx}
              type="button"
              disabled={disabled}
              onClick={() => onSelectQuestion(item.question)}
              className="group relative p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 hover:bg-slate-50 dark:hover:bg-slate-800/80 hover:border-cyan-500/50 transition-all duration-200 text-left disabled:opacity-50 disabled:pointer-events-none cursor-pointer flex flex-col justify-between shadow-sm"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-xl bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                      {item.icon}
                    </div>
                    <span className="text-[11px] font-bold text-slate-600 dark:text-slate-400">
                      {item.category}
                    </span>
                  </div>
                  <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-cyan-500 dark:group-hover:text-cyan-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all" />
                </div>
                <p className="text-xs sm:text-sm font-semibold text-slate-800 dark:text-slate-200 group-hover:text-slate-950 dark:group-hover:text-white transition-colors">
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

