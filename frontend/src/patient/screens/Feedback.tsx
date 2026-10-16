import React, { useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import type { RouteProp } from '@react-navigation/native';
import { useRoute } from '@react-navigation/native';

import type { PatientRootParamList } from '../navigator/PatientNavigator';
import { apiClient } from '../../shared/services/api';
import { Button, Card, ScreenContainer, SectionHeader } from '../../shared/components';

type FeedbackRoute = RouteProp<PatientRootParamList, 'Feedback'>;
type HelpAnswer = 'yes' | 'no' | 'not_sure';

export default function FeedbackScreen() {
  const { params } = useRoute<FeedbackRoute>();
  const [rating, setRating] = useState<number | null>(null);
  const [helped, setHelped] = useState<HelpAnswer | null>(null);
  const [npsScore, setNpsScore] = useState<number | null>(null);
  const [comments, setComments] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const submit = async () => {
    if (rating === null || helped === null || npsScore === null) {
      Alert.alert('A few answers are needed', 'Please select a star rating, answer whether the app helped, and choose an NPS score.');
      return;
    }
    setSubmitting(true);
    try {
      await apiClient.post('/api/v1/feedback', {
        appointment_id: params.appointmentId,
        rating,
        nps_score: npsScore,
        comments: [
          `Did Naviora AI help: ${helped.replace('_', ' ')}`,
          comments.trim() ? `Suggested improvement: ${comments.trim()}` : '',
        ].filter(Boolean).join('\n'),
      });
      setSubmitted(true);
      Alert.alert('Thank you', 'Your feedback has been recorded.');
    } catch (error: unknown) {
      const status = (error as { response?: { status?: number } }).response?.status;
      Alert.alert(status === 409 ? 'Feedback already submitted' : 'Could not submit feedback', status === 409 ? 'Feedback was already recorded for this visit.' : 'Check your connection and try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ScreenContainer>
      <ScrollView contentContainerStyle={styles.content}>
        <SectionHeader title="Tell us about your visit" />
        <Card style={styles.card}>
          <Text style={styles.question}>1. How would you rate your visit?</Text>
          <View style={styles.row}>
            {[1, 2, 3, 4, 5].map((value) => (
              <TouchableOpacity key={value} accessibilityRole="button" accessibilityLabel={`${value} stars`} onPress={() => setRating(value)} style={styles.choice}>
                <Text style={[styles.star, rating !== null && value <= rating && styles.selectedStar]}>{rating !== null && value <= rating ? '★' : '☆'}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <Text style={styles.question}>2. Did Naviora AI help during your visit?</Text>
          <View style={styles.row}>
            {(['yes', 'no', 'not_sure'] as const).map((value) => (
              <TouchableOpacity key={value} onPress={() => setHelped(value)} style={[styles.pill, helped === value && styles.selectedPill]}>
                <Text style={[styles.pillText, helped === value && styles.selectedPillText]}>{value === 'not_sure' ? 'Not sure' : value === 'yes' ? 'Yes' : 'No'}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <Text style={styles.question}>3. How likely are you to recommend this service? (0 = not at all, 10 = extremely likely)</Text>
          <View style={styles.scoreRow}>
            {Array.from({ length: 11 }, (_, score) => (
              <TouchableOpacity key={score} accessibilityRole="button" accessibilityLabel={`NPS ${score}`} onPress={() => setNpsScore(score)} style={[styles.score, npsScore === score && styles.selectedScore]}>
                <Text style={[styles.scoreText, npsScore === score && styles.selectedScoreText]}>{score}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <Text style={styles.question}>4. What could we improve? (optional)</Text>
          <TextInput value={comments} onChangeText={setComments} multiline maxLength={1000} placeholder="Your suggestion" style={styles.input} />
          <Button title={submitted ? 'Feedback recorded' : 'Send feedback'} onPress={() => void submit()} loading={submitting} disabled={submitting || submitted} />
        </Card>
      </ScrollView>
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  content: { padding: 16, paddingBottom: 32 },
  card: { gap: 16 },
  question: { color: '#1C1F24', fontSize: 16, fontWeight: '700', marginTop: 8 },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, alignItems: 'center' },
  choice: { padding: 4 },
  star: { color: '#8995A3', fontSize: 34 },
  selectedStar: { color: '#E8A838' },
  pill: { borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 18, paddingHorizontal: 16, paddingVertical: 10 },
  selectedPill: { backgroundColor: '#1D8A6C', borderColor: '#1D8A6C' },
  pillText: { color: '#1C1F24', fontWeight: '600' },
  selectedPillText: { color: '#fff' },
  scoreRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  score: { width: 34, height: 38, borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 8, alignItems: 'center', justifyContent: 'center' },
  selectedScore: { backgroundColor: '#1D8A6C', borderColor: '#1D8A6C' },
  scoreText: { color: '#1C1F24', fontWeight: '700' },
  selectedScoreText: { color: '#fff' },
  input: { minHeight: 88, borderWidth: 1, borderColor: '#DDE5EE', borderRadius: 10, padding: 12, textAlignVertical: 'top' },
});
