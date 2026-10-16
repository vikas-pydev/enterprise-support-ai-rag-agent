import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { SidebarNav } from '@/components/shell/SidebarNav';

describe('SidebarNav', () => {
  it('renders brand mark, new conversation, workspace navigation items, and external links', () => {
    const handleSelectTab = vi.fn();
    const handleNewConv = vi.fn();
    const handleOpenArch = vi.fn();

    render(
      <SidebarNav
        activeTab="home"
        onSelectTab={handleSelectTab}
        onNewConversation={handleNewConv}
        onOpenArchitecture={handleOpenArch}
      />
    );

    expect(screen.getByRole('button', { name: /Start New Conversation/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Workspace Home/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Policy Assistant/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Enterprise AI Agent/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Knowledge Base/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /View system architecture and tech stack/i })).toBeInTheDocument();
  });

  it('triggers onSelectTab when navigation items are clicked', async () => {
    const user = userEvent.setup();
    const handleSelectTab = vi.fn();
    const handleNewConv = vi.fn();
    const handleOpenArch = vi.fn();

    render(
      <SidebarNav
        activeTab="home"
        onSelectTab={handleSelectTab}
        onNewConversation={handleNewConv}
        onOpenArchitecture={handleOpenArch}
      />
    );

    await user.click(screen.getByRole('button', { name: /Policy Assistant/i }));
    expect(handleSelectTab).toHaveBeenCalledWith('rag');

    await user.click(screen.getByRole('button', { name: /Enterprise AI Agent/i }));
    expect(handleSelectTab).toHaveBeenCalledWith('agent');
  });

  it('triggers onOpenArchitecture when Architecture button is clicked', async () => {
    const user = userEvent.setup();
    const handleSelectTab = vi.fn();
    const handleOpenArch = vi.fn();

    render(
      <SidebarNav
        activeTab="home"
        onSelectTab={handleSelectTab}
        onOpenArchitecture={handleOpenArch}
      />
    );

    await user.click(screen.getByRole('button', { name: /View system architecture and tech stack/i }));
    expect(handleOpenArch).toHaveBeenCalled();
  });
});
