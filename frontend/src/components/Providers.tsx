'use client';
 
import React from 'react';
import { ToastProvider } from '@/components/ui';
import ChatbotWidget from '@/components/ChatbotWidget';
import AuthGate from '@/components/AuthGate';
 
export default function Providers({ children }: { children: React.ReactNode }) {
    const showChatbot = true;
 
    return (
        <ToastProvider>
            <AuthGate>
                {children}
                {showChatbot && <ChatbotWidget />}
            </AuthGate>
        </ToastProvider>
    );
}

