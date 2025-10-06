import React, { useEffect, useState, useMemo } from 'react';
import { View, Button } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import * as AuthSession from 'expo-auth-session';
import * as SecureStore from 'expo-secure-store';
import Constants from 'expo-constants';

import TodayScreen from './screens/TodayScreen';
import PhotosQAScreen from './screens/PhotosQAScreen';
import CloseoutScreen from './screens/CloseoutScreen';

const Stack = createStackNavigator();

export default function App() {
  const [token, setToken] = useState(null);

  // Auth0 discovery (hook) must be used inside a component
  const discovery = AuthSession.useAutoDiscovery(
    Constants.expoConfig?.extra?.AUTH0_DOMAIN || ''
  );

  useEffect(() => {
    const loadToken = async () => {
      try {
        const stored = await SecureStore.getItemAsync('authToken');
        if (stored) setToken(stored);
      } catch {}
    };
    loadToken();
  }, []);

  const login = async () => {
    try {
      const scheme = Constants.expoConfig?.scheme || 'nexa-enterprise';
      const redirectUri = AuthSession.makeRedirectUri({ scheme });
      const clientId = Constants.expoConfig?.extra?.AUTH0_CLIENT_ID;
      const audience = Constants.expoConfig?.extra?.AUTH0_AUDIENCE;

      const result = await AuthSession.startAsync({
        authUrl: `${discovery.authorizationEndpoint}?client_id=${clientId}` +
                 `&redirect_uri=${encodeURIComponent(redirectUri)}` +
                 `&response_type=code&audience=${encodeURIComponent(audience)}` +
                 `&scope=openid%20profile%20email`,
      });

      if (result.type === 'success') {
        const tokenResponse = await AuthSession.exchangeCodeAsync({
          clientId,
          code: result.params.code,
          redirectUri,
          extraParams: { audience },
        });
        await SecureStore.setItemAsync('authToken', tokenResponse.accessToken);
        setToken(tokenResponse.accessToken);
      }
    } catch (e) {
      console.warn('Auth error', e);
    }
  };

  if (!token) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <Button title="Login with Auth0" onPress={login} />
      </View>
    );
  }

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerStyle: { backgroundColor: '#F8FAFC' }, headerTintColor: '#4682B4' }}>
        <Stack.Screen name="Today" component={TodayScreen} />
        <Stack.Screen name="PhotosQA" component={PhotosQAScreen} />
        <Stack.Screen name="Closeout" component={CloseoutScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
