'use client';

import React, { useState, useEffect } from 'react';
import { Modal, useToast, Input } from '@/components/ui';
import { Button as UIButton } from '@/components/ui/Button';
import { createLead } from '@/lib/api';

type LeadCaptureSectionProps = {
    externalTrigger?: boolean;
    onExternalClose?: () => void;
    triggerReason?: 'chatbot_limit' | 'cta';
};

export default function LeadCaptureSection({
    externalTrigger = false,
    onExternalClose,
    triggerReason = 'cta',
}: LeadCaptureSectionProps) {
    const [modalOpen, setModalOpen] = useState(false);
    const [leadEmail, setLeadEmail] = useState('');
    const toast = useToast();

    useEffect(() => {
        if (externalTrigger) {
            setModalOpen(true);
        }
    }, [externalTrigger]);

    const handleClose = () => {
        setModalOpen(false);
        if (onExternalClose) {
            onExternalClose();
        }
    };

    return (
        <section className="py-40 px-6 bg-white relative overflow-hidden">
            {/* Decorative Background Glows */}
            <div className="absolute top-1/2 left-1/4 -translate-y-1/2 w-[600px] h-[600px] bg-teal-500/5 blur-[140px] rounded-full pointer-events-none" />
            <div className="absolute top-1/2 right-1/4 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-500/5 blur-[140px] rounded-full pointer-events-none" />

            <div className="max-w-5xl mx-auto relative z-10">
                <div className="relative p-16 md:p-24 rounded-[48px] bg-white/80 backdrop-blur-xl border-2 border-slate-200/60 shadow-2xl shadow-slate-200/50 text-center group transition-all duration-700 hover:shadow-[0_60px_100px_-30px_rgba(0,0,0,0.15)]">
                    <div className="relative z-10">
                        <h2 className="font-display text-4xl sm:text-5xl md:text-8xl font-bold mb-12 tracking-tight leading-tight italic text-slate-900 px-4">
                            Ready to{' '}
                            <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-600 via-cyan-500 to-indigo-600 not-italic inline-block">
                                Automate?
                            </span>
                        </h2>
                        <div className="space-y-4 mb-16">
                            <p className="font-body text-xl md:text-3xl font-medium text-slate-500 tracking-tight">
                                I&apos;m ready to analyze your next project.
                            </p>
                            <p className="font-display text-2xl md:text-4xl font-bold text-slate-900 tracking-tight">
                                The future of automation starts here.
                            </p>
                        </div>

                        <UIButton
                            onClick={() => setModalOpen(true)}
                            className="text-xl md:text-2xl px-16 py-8 h-auto font-bold shadow-xl transition-all group rounded-2xl bg-teal-600 hover:bg-teal-500 text-white hover:scale-105 active:scale-95 shadow-teal-600/30 hover:shadow-teal-600/50"
                        >
                            Start Your Engine
                        </UIButton>
                    </div>

                    {/* Subtle card decoration */}
                    <div className="absolute top-0 right-0 w-48 h-48 bg-gradient-to-br from-teal-500/5 to-transparent rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-1000" />
                    <div className="absolute bottom-0 left-0 w-48 h-48 bg-gradient-to-tr from-indigo-500/5 to-transparent rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-1000" />
                </div>
            </div>

            {/* Modal */}
            <Modal
                open={modalOpen}
                onClose={handleClose}
                title={triggerReason === 'chatbot_limit' ? '더 많은 질문이 필요하신가요?' : 'Get started'}
            >
                <div className="p-2">
                    {triggerReason === 'chatbot_limit' ? (
                        <p className="font-body text-lg text-slate-600 mb-8 leading-relaxed">
                            무료 체험이 종료되었습니다. 계속해서 AI 챗봇을 이용하시려면 이메일을 남겨주세요. 저희 팀이
                            24시간 내에 연락드리겠습니다.
                        </p>
                    ) : (
                        <p className="font-body text-lg text-slate-600 mb-8 leading-relaxed">
                            We&apos;ll help you set up your first pipeline. Leave your email and our team will reach out
                            within 24 hours.
                        </p>
                    )}
                    <Input
                        type="email"
                        placeholder="your@email.com"
                        className="mb-6 h-14 text-lg px-6 rounded-xl border-slate-200 focus:border-teal-600 focus:ring-teal-600/30"
                        value={leadEmail}
                        onChange={(e) => setLeadEmail(e.target.value)}
                    />
                    <UIButton
                        className="w-full h-14 text-xl font-bold rounded-xl bg-teal-600 hover:bg-teal-500 text-white"
                        onClick={async () => {
                            try {
                                await createLead({ email: leadEmail });
                                handleClose();
                                toast.addToast("Thanks! We'll be in touch soon.");
                                setLeadEmail('');
                            } catch {
                                toast.addToast('Failed to submit. Please try again.');
                            }
                        }}
                    >
                        Send Request
                    </UIButton>
                </div>
            </Modal>
        </section>
    );
}
