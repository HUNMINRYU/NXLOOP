'use client';

import { useState } from 'react';
import { Button } from '@/components/ui';

// Types for SNS content
interface InstagramPost {
  caption: string;
  hashtags: string[];
}

interface TwitterPost {
  content: string;
}

interface BlogPost {
  title: string;
  content: string;
}

interface SocialPosts {
  instagram?: InstagramPost;
  twitter?: TwitterPost;
  blog?: BlogPost;
}

interface SnsContentSectionProps {
  socialPosts?: SocialPosts | null;
}

type TabType = 'instagram' | 'twitter' | 'blog';

export function SnsContentSection({ socialPosts }: SnsContentSectionProps) {
  const [activeTab, setActiveTab] = useState<TabType>('instagram');
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const handleCopy = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  };

  if (!socialPosts) {
    return (
      <div className="text-center py-8 text-[var(--color-muted)]">
        <p>SNS 소재가 생성되지 않았습니다.</p>
        <p className="text-sm mt-1">파이프라인 실행 시 &quot;SNS 소재 생성&quot; 옵션을 활성화하세요.</p>
      </div>
    );
  }

  const tabs: { key: TabType; label: string; icon: string }[] = [
    { key: 'instagram', label: 'Instagram', icon: '📸' },
    { key: 'twitter', label: 'Twitter', icon: '🐦' },
    { key: 'blog', label: 'Blog', icon: '📝' },
  ];

  return (
    <div className="space-y-4">
      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-[var(--color-border)]">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? 'border-b-2 border-[var(--color-primary)] text-[var(--color-primary)]'
                : 'text-[var(--color-muted)] hover:text-[var(--color-foreground)]'
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Instagram Tab */}
      {activeTab === 'instagram' && socialPosts.instagram && (
        <div className="space-y-4">
          <div className="soft-section p-4 rounded-[var(--radius-md)]">
            <div className="flex justify-between items-start mb-2">
              <label className="text-xs font-bold text-[var(--color-muted)]">캡션</label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleCopy(socialPosts.instagram?.caption || '', 'caption')}
                className="text-xs"
              >
                {copiedField === 'caption' ? '✓ 복사됨' : '📋 복사'}
              </Button>
            </div>
            <p className="whitespace-pre-wrap text-sm">{socialPosts.instagram.caption}</p>
          </div>
          <div className="soft-section p-4 rounded-[var(--radius-md)]">
            <div className="flex justify-between items-start mb-2">
              <label className="text-xs font-bold text-[var(--color-muted)]">해시태그</label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleCopy(socialPosts.instagram?.hashtags?.join(' ') || '', 'hashtags')}
                className="text-xs"
              >
                {copiedField === 'hashtags' ? '✓ 복사됨' : '📋 복사'}
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {socialPosts.instagram.hashtags?.map((tag, idx) => (
                <span
                  key={idx}
                  className="px-2 py-1 bg-[var(--color-primary-light)] text-[var(--color-primary)] rounded-full text-xs"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Twitter Tab */}
      {activeTab === 'twitter' && socialPosts.twitter && (
        <div className="soft-section p-4 rounded-[var(--radius-md)]">
          <div className="flex justify-between items-start mb-2">
            <label className="text-xs font-bold text-[var(--color-muted)]">트윗 내용</label>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleCopy(socialPosts.twitter?.content || '', 'twitter')}
              className="text-xs"
            >
              {copiedField === 'twitter' ? '✓ 복사됨' : '📋 복사'}
            </Button>
          </div>
          <p className="whitespace-pre-wrap text-sm">{socialPosts.twitter.content}</p>
        </div>
      )}

      {/* Blog Tab */}
      {activeTab === 'blog' && socialPosts.blog && (
        <div className="space-y-4">
          <div className="soft-section p-4 rounded-[var(--radius-md)]">
            <div className="flex justify-between items-start mb-2">
              <label className="text-xs font-bold text-[var(--color-muted)]">제목</label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleCopy(socialPosts.blog?.title || '', 'blogTitle')}
                className="text-xs"
              >
                {copiedField === 'blogTitle' ? '✓ 복사됨' : '📋 복사'}
              </Button>
            </div>
            <h3 className="text-lg font-bold">{socialPosts.blog.title}</h3>
          </div>
          <div className="soft-section p-4 rounded-[var(--radius-md)]">
            <div className="flex justify-between items-start mb-2">
              <label className="text-xs font-bold text-[var(--color-muted)]">본문</label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleCopy(socialPosts.blog?.content || '', 'blogContent')}
                className="text-xs"
              >
                {copiedField === 'blogContent' ? '✓ 복사됨' : '📋 복사'}
              </Button>
            </div>
            <div className="whitespace-pre-wrap text-sm max-h-64 overflow-y-auto">
              {socialPosts.blog.content}
            </div>
          </div>
        </div>
      )}

      {/* Empty state for inactive tabs */}
      {activeTab === 'instagram' && !socialPosts.instagram && (
        <p className="text-center py-4 text-[var(--color-muted)]">Instagram 콘텐츠가 없습니다.</p>
      )}
      {activeTab === 'twitter' && !socialPosts.twitter && (
        <p className="text-center py-4 text-[var(--color-muted)]">Twitter 콘텐츠가 없습니다.</p>
      )}
      {activeTab === 'blog' && !socialPosts.blog && (
        <p className="text-center py-4 text-[var(--color-muted)]">Blog 콘텐츠가 없습니다.</p>
      )}
    </div>
  );
}
