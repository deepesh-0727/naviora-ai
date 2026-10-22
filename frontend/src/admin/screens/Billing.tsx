import React from 'react';
import AdminDataScreen from './AdminDataScreen';
export default function Billing() { return <AdminDataScreen title="Billing" endpoint="/admin/billing/bills" description="Persisted invoices, payments, and billing state" />; }
