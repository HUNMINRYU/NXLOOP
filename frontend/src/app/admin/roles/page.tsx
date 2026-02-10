'use client';

import { useState, useEffect } from 'react';
import AdminRolesClient, { type Role, type Team } from '@/components/AdminRolesClient';
import { fetchRoles, fetchTeams } from '@/lib/api';

export default function AdminRolesPage() {
    const [initialRoles, setInitialRoles] = useState<Role[]>([]);
    const [initialTeams, setInitialTeams] = useState<Team[]>([]);

    useEffect(() => {
        const loadData = async () => {
            try {
                const [roleData, teamData] = await Promise.all([fetchRoles(), fetchTeams()]);
                setInitialRoles(roleData?.roles || []);
                setInitialTeams(teamData?.teams || []);
            } catch {
                console.error('[Client] Failed to fetch roles/teams.');
            }
        };
        loadData();
    }, []);

    return <AdminRolesClient initialRoles={initialRoles} initialTeams={initialTeams} />;
}
