import React, { useEffect, useRef } from 'react';
import { Animated, StyleSheet, View, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAlert } from '../../context/AlertContext';
import { useTheme } from '../../context/ThemeContext';
import { NavioraText } from './AtomicComponents';

export const GlobalAlert = () => {
  const { alert, hideAlert } = useAlert();
  const theme = useTheme();
  const slideAnim = useRef(new Animated.Value(-100)).current;

  useEffect(() => {
    if (alert.visible) {
      Animated.spring(slideAnim, {
        toValue: 20,
        useNativeDriver: true,
      }).start();
    } else {
      Animated.timing(slideAnim, {
        toValue: -150,
        duration: 300,
        useNativeDriver: true,
      }).start();
    }
  }, [alert.visible]);

  if (!alert.visible && (slideAnim as any).__getValue() === -150) return null;

  const getIcon = () => {
    switch (alert.type) {
      case 'success': return 'checkmark-circle';
      case 'error': return 'alert-circle';
      case 'warning': return 'warning';
      default: return 'information-circle';
    }
  };

  const getColor = () => {
    switch (alert.type) {
      case 'success': return theme.colors.accent;
      case 'error': return theme.colors.error;
      case 'warning': return theme.colors.warning;
      default: return theme.colors.primary;
    }
  };

  return (
    <Animated.View style={[
      styles.container,
      {
        transform: [{ translateY: slideAnim }],
        backgroundColor: theme.colors.surface,
        borderColor: theme.colors.surfaceVariant,
        borderLeftColor: getColor(),
      }
    ]}>
      <View style={styles.content}>
        <Ionicons name={getIcon()} size={24} color={getColor()} />
        <NavioraText style={styles.message}>{alert.message}</NavioraText>
        <TouchableOpacity onPress={hideAlert} style={styles.close}>
          <Ionicons name="close" size={20} color={theme.colors.text.low} />
        </TouchableOpacity>
      </View>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 50,
    left: 20,
    right: 20,
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderLeftWidth: 6,
    zIndex: 9999,
    elevation: 10,
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 5 },
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  message: {
    flex: 1,
    marginLeft: 12,
    fontSize: 14,
  },
  close: {
    padding: 4,
  }
});
