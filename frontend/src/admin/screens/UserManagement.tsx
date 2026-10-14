import React from 'react';
import AdminDataScreen from './AdminDataScreen';
export default function UserManagement() { return <AdminDataScreen title="Users" endpoint="/api/v1/admin/users" description="Hospital accounts, roles, and account state" />; }
