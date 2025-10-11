/**
 * NEXA Mobile App - Main Entry Point
 * Simple, clean entry point that delegates to MainApp
 */

import React from 'react';
import { SafeAreaView, StyleSheet } from 'react-native';
import MainApp from './src/screens/MainApp';

export default function App() {
  return (
    <SafeAreaView style={styles.container}>
      <MainApp />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
});
