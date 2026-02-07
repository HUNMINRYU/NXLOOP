'use client';

import { useState } from 'react';
import { Navbar } from '@/features/landing';
import { Button, Card, Input } from '@/components/ui';
import { createRole, createTeam, fetchRoles, fetchTeams } from '@/lib/api';

export interface Role {
  id: number;
  name: string;
  description?: string | null;
}

export interface Team {
  id: number;
  name: string;
}

interface AdminRolesClientProps {
  initialRoles: Role[];
  initialTeams: Team[];
}

export default function AdminRolesClient({ initialRoles, initialTeams }: AdminRolesClientProps) {
  const [roles, setRoles] = useState(initialRoles);
  const [teams, setTeams] = useState(initialTeams);
  const [roleName, setRoleName] = useState('');
  const [roleDesc, setRoleDesc] = useState('');
  const [teamName, setTeamName] = useState('');
  const [message, setMessage] = useState('');

  const loadData = async () => {
    try {
      const [roleData, teamData] = await Promise.all([fetchRoles(), fetchTeams()]);
      setRoles(roleData.roles || []);
      setTeams(teamData.teams || []);
    } catch {
      setMessage('데이터 갱신 실패');
    }
  };

  const handleCreateRole = async () => {
    setMessage('');
    if (!roleName.trim()) {
      setMessage('역할 이름을 입력하세요.');
      return;
    }
    await createRole({ name: roleName.trim(), description: roleDesc.trim() || undefined });
    setRoleName('');
    setRoleDesc('');
    await loadData();
  };

  const handleCreateTeam = async () => {
    setMessage('');
    if (!teamName.trim()) {
      setMessage('팀 이름을 입력하세요.');
      return;
    }
    await createTeam({ name: teamName.trim() });
    setTeamName('');
    await loadData();
  };

  return (
    <>
      <Navbar />
      <main className="relative min-h-screen overflow-hidden">
        {/* Light Elegant Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-slate-100" />
        <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500/[0.02] via-transparent to-purple-500/[0.02]" />
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `
              linear-gradient(to right, rgb(15 23 42 / 0.08) 1px, transparent 1px),
              linear-gradient(to bottom, rgb(15 23 42 / 0.08) 1px, transparent 1px)
            `,
            backgroundSize: '80px 80px',
          }}
        />
        <div className="absolute top-20 -left-20 w-[600px] h-[600px] bg-indigo-400/[0.06] blur-[140px] rounded-full" />
        <div className="absolute bottom-20 -right-20 w-[600px] h-[600px] bg-purple-400/[0.06] blur-[140px] rounded-full" />

        <div className="relative z-10 p-8 pt-24">
        <div className="max-w-5xl mx-auto space-y-8">
          <Card className="p-6 border-slate-200/60 bg-white/80 backdrop-blur-xl shadow-lg shadow-slate-200/50">
            <p className="font-display font-semibold text-indigo-600 uppercase tracking-[0.2em] text-sm mb-1">Admin</p>
            <h1 className="font-display text-2xl font-bold text-slate-900 mb-2">Role / Team 관리</h1>
            <p className="font-body text-base text-slate-600 mb-4">역할과 팀 정보를 관리합니다.</p>

            {message && <p className="text-sm text-rose-600 font-medium mb-4">{message}</p>}

            <Card className="p-6 mb-6 border-slate-200/60 bg-slate-50/60">
              <Card.Title className="mb-4 text-slate-900">역할 생성</Card.Title>
              <div className="grid gap-3 md:grid-cols-2 mb-4">
                <Input placeholder="role name" value={roleName} onChange={(e) => setRoleName(e.target.value)} className="bg-white border-slate-200 focus:ring-indigo-500/30 focus:border-indigo-500 text-slate-900" />
                <Input placeholder="description (optional)" value={roleDesc} onChange={(e) => setRoleDesc(e.target.value)} className="bg-white border-slate-200 focus:ring-indigo-500/30 focus:border-indigo-500 text-slate-900" />
              </div>
              <Button variant="secondary" onClick={handleCreateRole} className="bg-slate-900 hover:bg-slate-800 text-white font-semibold">역할 추가</Button>
              <div className="space-y-2 mt-4">
                {roles.map((role) => (
                  <div key={role.id} className="border border-slate-200 rounded-2xl p-3 text-sm font-medium text-slate-900 bg-white">
                    {role.name} {role.description ? `- ${role.description}` : ''}
                  </div>
                ))}
              </div>
            </Card>

            <Card className="p-6 border-slate-200/60 bg-slate-50/60">
              <Card.Title className="mb-4 text-slate-900">팀 생성</Card.Title>
              <div className="flex gap-3 mb-4">
                <Input className="flex-1 bg-white border-slate-200 focus:ring-indigo-500/30 focus:border-indigo-500 text-slate-900" placeholder="team name" value={teamName} onChange={(e) => setTeamName(e.target.value)} />
                <Button variant="secondary" onClick={handleCreateTeam} className="bg-slate-900 hover:bg-slate-800 text-white font-semibold">팀 추가</Button>
              </div>
              <div className="space-y-2">
                {teams.map((team) => (
                  <div key={team.id} className="border border-slate-200 rounded-2xl p-3 text-sm font-medium text-slate-900 bg-white">
                    {team.name}
                  </div>
                ))}
              </div>
            </Card>
          </Card>
        </div>
        </div>
      </main>
    </>
  );
}

