import React from 'react';
import AdminDataScreen from './AdminDataScreen';
export default function DepartmentManagement() { return <AdminDataScreen title="Departments" endpoint="/api/v1/admin/departments" description="Configured departments and contact details" />; }
