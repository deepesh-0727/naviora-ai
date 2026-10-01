import React, { useState, useEffect, useCallback } from 'react';
import {
  StyleSheet, View, ScrollView, TouchableOpacity, SafeAreaView,
  Modal, ActivityIndicator, Dimensions, Linking, Alert
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, { FadeInUp, FadeIn } from 'react-native-reanimated';

import { useTheme } from '../context/ThemeContext';
import { NavioraText, GlassCard, StatusBadge, GradientButton } from '../components/common/AtomicComponents';
import { apiService } from '../services/api';

const { width } = Dimensions.get('window');

type InvoiceStatus = 'pending' | 'paid' | 'overdue' | 'cancelled';
type TabFilter = 'all' | 'pending' | 'paid';

interface InvoiceItem {
  name: string;
  quantity: number;
  price: number;
}

interface Invoice {
  id: number;
  invoice_number: string;
  amount: number;
  status: InvoiceStatus;
  payment_method?: string;
  transaction_id?: string;
  items: InvoiceItem[];
  created_at: string;
  appointment_id?: number;
}

// ─── Status helpers ───────────────────────────────────────────────────────────

const STATUS_META: Record<InvoiceStatus, { color: string; icon: string; label: string }> = {
  pending: { color: '#F59E0B', icon: 'time-outline',         label: 'Pending'   },
  paid:    { color: '#10B981', icon: 'checkmark-circle',     label: 'Paid'      },
  overdue: { color: '#EF4444', icon: 'alert-circle-outline', label: 'Overdue'   },
  cancelled:{ color: '#6B7280',icon: 'close-circle-outline', label: 'Cancelled' },
};

const formatDate = (iso: string) => {
  try {
    return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch { return iso; }
};

const formatINR = (amount: number) =>
  `₹${amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

// ─── Invoice Card ─────────────────────────────────────────────────────────────

const InvoiceCard = ({ invoice, index, onPayPress, onDetailPress, theme }: {
  invoice: Invoice; index: number; theme: any;
  onPayPress: (inv: Invoice) => void;
  onDetailPress: (inv: Invoice) => void;
}) => {
  const meta = STATUS_META[invoice.status] || STATUS_META.pending;

  return (
    <Animated.View entering={FadeInUp.delay(index * 80)}>
      <TouchableOpacity onPress={() => onDetailPress(invoice)} activeOpacity={0.85}>
        <GlassCard style={styles.invoiceCard}>
          {/* Header row */}
          <View style={styles.cardHeader}>
            <View style={[styles.invoiceIcon, { backgroundColor: meta.color + '20' }]}>
              <Ionicons name="document-text" size={22} color={meta.color} />
            </View>
            <View style={{ flex: 1, marginLeft: 14 }}>
              <NavioraText type="label" style={{ color: meta.color, letterSpacing: 0.5 }}>
                {invoice.invoice_number}
              </NavioraText>
              <NavioraText type="xs" color="low">{formatDate(invoice.created_at)}</NavioraText>
            </View>
            <View style={[styles.statusPill, { backgroundColor: meta.color + '20' }]}>
              <Ionicons name={meta.icon as any} size={12} color={meta.color} />
              <NavioraText type="xs" style={{ color: meta.color, marginLeft: 4 }}>{meta.label}</NavioraText>
            </View>
          </View>

          <View style={styles.cardDivider} />

          {/* Amount + action */}
          <View style={styles.cardFooter}>
            <View>
              <NavioraText type="xs" color="low">TOTAL DUE</NavioraText>
              <NavioraText type="h2" style={{ color: '#F8FAFC' }}>{formatINR(invoice.amount)}</NavioraText>
            </View>
            {invoice.status === 'pending' || invoice.status === 'overdue' ? (
              <TouchableOpacity
                style={[styles.payBtn, { backgroundColor: theme.colors.primary }]}
                onPress={() => onPayPress(invoice)}
              >
                <Ionicons name="card" size={16} color="#FFF" />
                <NavioraText type="label" style={{ color: '#FFF', marginLeft: 6 }}>Pay Now</NavioraText>
              </TouchableOpacity>
            ) : (
              <View style={[styles.payBtn, { backgroundColor: '#10B98120' }]}>
                <Ionicons name="checkmark" size={16} color="#10B981" />
                <NavioraText type="label" style={{ color: '#10B981', marginLeft: 6 }}>Settled</NavioraText>
              </View>
            )}
          </View>

          {/* Items preview */}
          {invoice.items && invoice.items.length > 0 && (
            <View style={styles.itemsPreview}>
              {invoice.items.slice(0, 2).map((item, i) => (
                <NavioraText key={i} type="xs" color="low">
                  • {item.name}  {formatINR(item.price)}
                </NavioraText>
              ))}
              {invoice.items.length > 2 && (
                <NavioraText type="xs" color="low">
                  + {invoice.items.length - 2} more items
                </NavioraText>
              )}
            </View>
          )}
        </GlassCard>
      </TouchableOpacity>
    </Animated.View>
  );
};

// ─── Invoice Detail Modal ─────────────────────────────────────────────────────

const InvoiceDetailModal = ({ invoice, visible, onClose, onPay, theme }: {
  invoice: Invoice | null; visible: boolean; theme: any;
  onClose: () => void; onPay: () => void;
}) => {
  if (!invoice) return null;
  const meta = STATUS_META[invoice.status] || STATUS_META.pending;

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View style={styles.modalOverlay}>
        <Animated.View entering={FadeIn} style={[styles.modalSheet, { backgroundColor: '#161B2C', borderColor: 'rgba(255,255,255,0.1)' }]}>
          {/* Handle */}
          <View style={styles.modalHandle} />

          <ScrollView showsVerticalScrollIndicator={false}>
            {/* Invoice header */}
            <View style={styles.modalHeader}>
              <View>
                <NavioraText type="h2">Invoice Detail</NavioraText>
                <NavioraText type="xs" color="low">{invoice.invoice_number}</NavioraText>
              </View>
              <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
                <Ionicons name="close" size={22} color="#94A3B8" />
              </TouchableOpacity>
            </View>

            {/* Status banner */}
            <View style={[styles.statusBanner, { backgroundColor: meta.color + '15', borderColor: meta.color + '40' }]}>
              <Ionicons name={meta.icon as any} size={18} color={meta.color} />
              <NavioraText type="label" style={{ color: meta.color, marginLeft: 8 }}>
                {meta.label.toUpperCase()} — {formatDate(invoice.created_at)}
              </NavioraText>
            </View>

            {/* Line items */}
            <NavioraText type="label" color="low" style={styles.sectionLabel}>ITEMISED BREAKDOWN</NavioraText>
            <GlassCard style={{ padding: 0, overflow: 'hidden' }}>
              {(invoice.items || []).map((item, i) => (
                <View key={i} style={[styles.lineItem, i > 0 && { borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.05)' }]}>
                  <View style={{ flex: 1 }}>
                    <NavioraText type="body">{item.name}</NavioraText>
                    <NavioraText type="xs" color="low">Qty: {item.quantity}</NavioraText>
                  </View>
                  <NavioraText type="label" style={{ color: '#F8FAFC' }}>{formatINR(item.price)}</NavioraText>
                </View>
              ))}
            </GlassCard>

            {/* Total */}
            <GlassCard style={styles.totalCard}>
              <View style={styles.totalRow}>
                <NavioraText type="body" color="low">Subtotal</NavioraText>
                <NavioraText type="body">{formatINR(invoice.amount / 1.18)}</NavioraText>
              </View>
              <View style={styles.totalRow}>
                <NavioraText type="body" color="low">GST (18%)</NavioraText>
                <NavioraText type="body">{formatINR(invoice.amount - invoice.amount / 1.18)}</NavioraText>
              </View>
              <View style={[styles.totalRow, styles.grandTotal]}>
                <NavioraText type="h3">Total</NavioraText>
                <NavioraText type="h2" style={{ color: '#0EA5E9' }}>{formatINR(invoice.amount)}</NavioraText>
              </View>
            </GlassCard>

            {/* Payment info if paid */}
            {invoice.status === 'paid' && invoice.transaction_id && (
              <GlassCard style={{ padding: 16, marginTop: 16 }}>
                <NavioraText type="label" color="low">PAYMENT REFERENCE</NavioraText>
                <NavioraText type="body" style={{ marginTop: 4 }}>{invoice.transaction_id}</NavioraText>
                {invoice.payment_method && (
                  <NavioraText type="xs" color="low" style={{ marginTop: 4 }}>via {invoice.payment_method}</NavioraText>
                )}
              </GlassCard>
            )}

            {/* Pay button */}
            {(invoice.status === 'pending' || invoice.status === 'overdue') && (
              <GradientButton
                title={`Pay ${formatINR(invoice.amount)}`}
                onPress={onPay}
                style={{ marginTop: 24 }}
              />
            )}

            <View style={{ height: 40 }} />
          </ScrollView>
        </Animated.View>
      </View>
    </Modal>
  );
};

// ─── Payment Modal ────────────────────────────────────────────────────────────

const PaymentModal = ({ invoice, visible, onClose, onSuccess, theme }: {
  invoice: Invoice | null; visible: boolean; theme: any;
  onClose: () => void; onSuccess: (inv: Invoice) => void;
}) => {
  const [processing, setProcessing] = useState(false);
  const [selectedMethod, setSelectedMethod] = useState<'UPI' | 'Card' | 'Net Banking'>('UPI');

  const methods: Array<{ id: typeof selectedMethod; icon: string; label: string }> = [
    { id: 'UPI',         icon: 'qr-code-outline',   label: 'UPI / Scanner'   },
    { id: 'Card',        icon: 'card-outline',       label: 'Credit / Debit'  },
    { id: 'Net Banking', icon: 'globe-outline',      label: 'Net Banking'     },
  ];

  const handlePay = async () => {
    if (!invoice) return;
    setProcessing(true);
    try {
      // Step 1: Create Razorpay order
      const orderRes = await apiService.post<any>('/billing/create-razorpay-order', {
        invoice_id: invoice.id,
        amount: invoice.amount,
      });

      if (!orderRes.data?.order_id) throw new Error('Failed to create payment order');

      // Step 2: Deep-link to Razorpay or handle in-app
      // In a full React Native + Razorpay SDK integration, you'd call RazorpayCheckout.open()
      // For now we simulate — real integration uses @razorpay/react-native-razorpay
      const razorpayUrl = `https://razorpay.com/payment-link/${orderRes.data.order_id}`;
      const canOpen = await Linking.canOpenURL(razorpayUrl);
      if (canOpen) {
        await Linking.openURL(razorpayUrl);
      }

      // Step 3: Poll or use webhook-confirmed payment mark
      // After redirect back, webhook updates status; user refreshes via onSuccess
      onSuccess(invoice);
    } catch (err: any) {
      Alert.alert('Payment Failed', err.message || 'Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  if (!invoice) return null;

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View style={styles.modalOverlay}>
        <Animated.View entering={FadeIn} style={[styles.modalSheet, { backgroundColor: '#161B2C', borderColor: 'rgba(255,255,255,0.1)' }]}>
          <View style={styles.modalHandle} />

          <View style={styles.modalHeader}>
            <NavioraText type="h2">Make Payment</NavioraText>
            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <Ionicons name="close" size={22} color="#94A3B8" />
            </TouchableOpacity>
          </View>

          {/* Amount */}
          <GlassCard style={styles.amountCard}>
            <NavioraText type="xs" color="low">AMOUNT DUE</NavioraText>
            <NavioraText type="h1" style={{ color: '#0EA5E9', marginTop: 4 }}>
              {formatINR(invoice.amount)}
            </NavioraText>
            <NavioraText type="xs" color="low" style={{ marginTop: 4 }}>
              {invoice.invoice_number}
            </NavioraText>
          </GlassCard>

          {/* Payment method selector */}
          <NavioraText type="label" color="low" style={[styles.sectionLabel, { marginTop: 24 }]}>
            PAYMENT METHOD
          </NavioraText>
          {methods.map(m => (
            <TouchableOpacity
              key={m.id}
              onPress={() => setSelectedMethod(m.id)}
              style={[
                styles.methodRow,
                { borderColor: selectedMethod === m.id ? theme.colors.primary : 'rgba(255,255,255,0.1)' },
                selectedMethod === m.id && { backgroundColor: theme.colors.primary + '15' },
              ]}
            >
              <Ionicons name={m.icon as any} size={22} color={selectedMethod === m.id ? theme.colors.primary : '#94A3B8'} />
              <NavioraText type="body" style={{ flex: 1, marginLeft: 14 }}>{m.label}</NavioraText>
              {selectedMethod === m.id && <Ionicons name="checkmark-circle" size={20} color={theme.colors.primary} />}
            </TouchableOpacity>
          ))}

          {/* Secure badge */}
          <View style={styles.secureBadge}>
            <Ionicons name="lock-closed" size={14} color="#10B981" />
            <NavioraText type="xs" style={{ color: '#10B981', marginLeft: 6 }}>
              Secured by Razorpay · PCI-DSS Compliant
            </NavioraText>
          </View>

          {/* Pay button */}
          <GradientButton
            title={processing ? 'Processing…' : `Pay Securely — ${formatINR(invoice.amount)}`}
            onPress={handlePay}
            style={{ marginTop: 24 }}
          />
          {processing && <ActivityIndicator color={theme.colors.primary} style={{ marginTop: 12 }} />}

          <View style={{ height: 40 }} />
        </Animated.View>
      </View>
    </Modal>
  );
};

// ─── Main Screen ──────────────────────────────────────────────────────────────

export default function BillingScreen({ navigation }: any) {
  const theme = useTheme();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<TabFilter>('all');
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [payVisible, setPayVisible] = useState(false);

  const fetchInvoices = useCallback(async () => {
    setLoading(true);
    const res = await apiService.get<Invoice[]>('/billing/invoices');
    setLoading(false);
    if (res.data) setInvoices(Array.isArray(res.data) ? res.data : []);
  }, []);

  useEffect(() => { fetchInvoices(); }, [fetchInvoices]);

  const filtered = invoices.filter(inv => {
    if (tab === 'pending') return inv.status === 'pending' || inv.status === 'overdue';
    if (tab === 'paid')    return inv.status === 'paid';
    return true;
  });

  const totalPending = invoices
    .filter(i => i.status === 'pending' || i.status === 'overdue')
    .reduce((s, i) => s + i.amount, 0);

  const tabs: Array<{ id: TabFilter; label: string }> = [
    { id: 'all',     label: 'All'     },
    { id: 'pending', label: 'Pending' },
    { id: 'paid',    label: 'Paid'    },
  ];

  return (
    <LinearGradient colors={theme.colors.gradients.primary} style={styles.container}>
      <StatusBar style="light" />
      <SafeAreaView style={{ flex: 1 }}>

        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
            <Ionicons name="chevron-back" size={28} color="#FFF" />
          </TouchableOpacity>
          <NavioraText type="h2" style={{ flex: 1, marginLeft: 12 }}>My Bills</NavioraText>
          <TouchableOpacity style={styles.iconBtn} onPress={fetchInvoices}>
            <Ionicons name="refresh-outline" size={22} color="#FFF" />
          </TouchableOpacity>
        </View>

        {/* Pending summary card */}
        {totalPending > 0 && (
          <Animated.View entering={FadeInUp} style={styles.summaryWrapper}>
            <GlassCard style={[styles.summaryCard, { borderColor: '#F59E0B40' }]}>
              <View style={styles.summaryRow}>
                <View style={[styles.summaryIcon, { backgroundColor: '#F59E0B20' }]}>
                  <Ionicons name="alert-circle" size={22} color="#F59E0B" />
                </View>
                <View style={{ flex: 1, marginLeft: 14 }}>
                  <NavioraText type="xs" style={{ color: '#F59E0B' }}>OUTSTANDING BALANCE</NavioraText>
                  <NavioraText type="h2">{formatINR(totalPending)}</NavioraText>
                </View>
              </View>
            </GlassCard>
          </Animated.View>
        )}

        {/* Tab filter */}
        <View style={styles.tabRow}>
          {tabs.map(t => (
            <TouchableOpacity
              key={t.id}
              onPress={() => setTab(t.id)}
              style={[
                styles.tabBtn,
                tab === t.id && { backgroundColor: theme.colors.primary + '30', borderColor: theme.colors.primary },
                { borderColor: tab === t.id ? theme.colors.primary : 'rgba(255,255,255,0.1)' },
              ]}
            >
              <NavioraText type="label" style={{ color: tab === t.id ? theme.colors.primary : '#94A3B8' }}>
                {t.label}
              </NavioraText>
            </TouchableOpacity>
          ))}
        </View>

        {/* Invoice list */}
        {loading ? (
          <View style={styles.loadingBox}>
            <ActivityIndicator size="large" color={theme.colors.primary} />
            <NavioraText type="body" color="low" style={{ marginTop: 12 }}>Loading invoices…</NavioraText>
          </View>
        ) : (
          <ScrollView
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
          >
            {filtered.length === 0 ? (
              <Animated.View entering={FadeIn} style={styles.emptyState}>
                <Ionicons name="document-text-outline" size={64} color="#334155" />
                <NavioraText type="h3" color="low" style={{ marginTop: 16 }}>No invoices found</NavioraText>
                <NavioraText type="body" color="low" style={{ textAlign: 'center', marginTop: 8 }}>
                  {tab === 'pending' ? 'You have no outstanding bills.' : 'No billing records yet.'}
                </NavioraText>
              </Animated.View>
            ) : (
              filtered.map((inv, idx) => (
                <InvoiceCard
                  key={inv.id}
                  invoice={inv}
                  index={idx}
                  theme={theme}
                  onPayPress={(i) => { setSelectedInvoice(i); setPayVisible(true); }}
                  onDetailPress={(i) => { setSelectedInvoice(i); setDetailVisible(true); }}
                />
              ))
            )}
            <View style={{ height: 120 }} />
          </ScrollView>
        )}
      </SafeAreaView>

      {/* Modals */}
      <InvoiceDetailModal
        invoice={selectedInvoice}
        visible={detailVisible}
        theme={theme}
        onClose={() => setDetailVisible(false)}
        onPay={() => { setDetailVisible(false); setPayVisible(true); }}
      />
      <PaymentModal
        invoice={selectedInvoice}
        visible={payVisible}
        theme={theme}
        onClose={() => setPayVisible(false)}
        onSuccess={() => { setPayVisible(false); fetchInvoices(); }}
      />
    </LinearGradient>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { flexDirection: 'row', alignItems: 'center', padding: 24 },
  backBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: 'rgba(255,255,255,0.05)', justifyContent: 'center', alignItems: 'center' },
  iconBtn:  { width: 44, height: 44, borderRadius: 22, backgroundColor: 'rgba(255,255,255,0.05)', justifyContent: 'center', alignItems: 'center' },

  summaryWrapper: { paddingHorizontal: 24, marginBottom: 16 },
  summaryCard: { padding: 20, borderWidth: 1 },
  summaryRow: { flexDirection: 'row', alignItems: 'center' },
  summaryIcon: { width: 44, height: 44, borderRadius: 14, justifyContent: 'center', alignItems: 'center' },

  tabRow: { flexDirection: 'row', paddingHorizontal: 24, gap: 10, marginBottom: 20 },
  tabBtn: { flex: 1, paddingVertical: 10, borderRadius: 14, borderWidth: 1, alignItems: 'center' },

  scrollContent: { paddingHorizontal: 24 },
  loadingBox: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyState: { alignItems: 'center', paddingVertical: 80 },

  invoiceCard: { padding: 20, marginBottom: 16 },
  cardHeader: { flexDirection: 'row', alignItems: 'center' },
  invoiceIcon: { width: 46, height: 46, borderRadius: 14, justifyContent: 'center', alignItems: 'center' },
  statusPill: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 20 },
  cardDivider: { height: 1, backgroundColor: 'rgba(255,255,255,0.06)', marginVertical: 14 },
  cardFooter: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  payBtn: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 18, paddingVertical: 10, borderRadius: 14 },
  itemsPreview: { marginTop: 14, gap: 4 },

  // Modals
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  modalSheet: { borderTopLeftRadius: 32, borderTopRightRadius: 32, borderTopWidth: 1, padding: 24, maxHeight: '90%' },
  modalHandle: { width: 44, height: 4, borderRadius: 2, backgroundColor: 'rgba(255,255,255,0.2)', alignSelf: 'center', marginBottom: 20 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  closeBtn: { width: 36, height: 36, borderRadius: 18, backgroundColor: 'rgba(255,255,255,0.08)', justifyContent: 'center', alignItems: 'center' },

  statusBanner: { flexDirection: 'row', alignItems: 'center', padding: 14, borderRadius: 16, borderWidth: 1, marginBottom: 20 },
  sectionLabel: { letterSpacing: 1.5, marginBottom: 12, fontWeight: '800' },
  lineItem: { flexDirection: 'row', alignItems: 'center', padding: 16 },

  totalCard: { padding: 20, marginTop: 16 },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 },
  grandTotal: { marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.08)', marginBottom: 0 },

  amountCard: { padding: 24, alignItems: 'center', marginBottom: 8 },
  methodRow: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderRadius: 16, padding: 16, marginBottom: 12 },
  secureBadge: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginTop: 8 },
});
