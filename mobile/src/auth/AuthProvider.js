import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import * as AuthSession from 'expo-auth-session';
import * as SecureStore from 'expo-secure-store';
import Constants from 'expo-constants';

const AuthContext = createContext(null);

const TOKEN_KEY = 'nexa_auth_token_v1';
const REFRESH_TOKEN_KEY = 'nexa_refresh_token_v1';
const USER_KEY = 'nexa_user_v1';

export function AuthProvider({ children }) {
  const extra = Constants?.expoConfig?.extra || {};
  const domain = extra.AUTH0_DOMAIN;
  const clientId = extra.AUTH0_CLIENT_ID;
  const audience = extra.AUTH0_AUDIENCE;
  const scheme = extra.REDIRECT_SCHEME || 'nexaapp';

  const discovery = AuthSession.useAutoDiscovery(`https://${domain}`);
  const redirectUri = AuthSession.makeRedirectUri({ scheme });

  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [accessToken, setAccessToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);
  const [user, setUser] = useState(null);

  useEffect(() => {
    (async () => {
      const t = await SecureStore.getItemAsync(TOKEN_KEY);
      const r = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
      const u = await SecureStore.getItemAsync(USER_KEY);
      if (t) setAccessToken(t);
      if (r) setRefreshToken(r);
      if (u) setUser(JSON.parse(u));
      setIsAuthenticated(!!t);
    })();
  }, []);

  const login = async () => {
    try {
      // Manual auth request (without hook inside callback)
      const request = new AuthSession.AuthRequest({
        clientId,
        redirectUri,
        scopes: ['openid', 'profile', 'email', 'offline_access'],
        extraParams: { audience },
        usePKCE: true,
      });
      await request.makeAuthUrlAsync(discovery);
      const result = await request.promptAsync(discovery);
      if (result.type === 'success') {
        const tokenResponse = await AuthSession.exchangeCodeAsync(
          {
            clientId,
            code: result.params.code,
            redirectUri,
            extraParams: { code_verifier: request.codeVerifier, audience },
          },
          discovery
        );
        const { access_token, refresh_token, id_token } = tokenResponse;
        const userInfoRes = await fetch(discovery.userInfoEndpoint, {
          headers: { Authorization: `Bearer ${access_token}` },
        });
        const userInfo = await userInfoRes.json();

        await SecureStore.setItemAsync(TOKEN_KEY, access_token);
        if (refresh_token) await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refresh_token);
        await SecureStore.setItemAsync(USER_KEY, JSON.stringify(userInfo));

        setAccessToken(access_token);
        setRefreshToken(refresh_token || null);
        setUser(userInfo);
        setIsAuthenticated(true);
      }
    } catch (err) {
      console.error('Auth error:', err);
    }
  };

  const devLogin = async () => {
    // Dev bypass: mark authenticated with a dummy user
    const dummy = { sub: 'dev-user', org_id: 'dev-org', roles: ['admin'] };
    await SecureStore.setItemAsync(USER_KEY, JSON.stringify(dummy));
    setUser(dummy);
    setIsAuthenticated(true);
  };

  const logout = async () => {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
    await SecureStore.deleteItemAsync(USER_KEY);
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
    setIsAuthenticated(false);
  };

  const value = useMemo(
    () => ({ isAuthenticated, accessToken, refreshToken, user, login, devLogin, logout }),
    [isAuthenticated, accessToken, refreshToken, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export async function fetchWithAuth(url, options = {}, accessToken) {
  const headers = {
    ...(options.headers || {}),
    Authorization: `Bearer ${accessToken}`,
    'Content-Type': 'application/json',
  };
  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json();
}
