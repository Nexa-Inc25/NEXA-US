import React, { createContext, useContext, useState, useEffect } from 'react';

interface User {
  name: string;
  role: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  login: (role: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    // Check for existing session
    const role = sessionStorage.getItem('userRole');
    const name = sessionStorage.getItem('userName');
    if (role && name) {
      setUser({
        name,
        role,
        email: role === 'general_foreman' ? 'john.smith@nexa.com' : 'mike.johnson@nexa.com'
      });
    }
  }, []);

  const login = (role: string) => {
    const userData = {
      name: role === 'general_foreman' ? 'John Smith' : 'Mike Johnson',
      role,
      email: role === 'general_foreman' ? 'john.smith@nexa.com' : 'mike.johnson@nexa.com'
    };
    setUser(userData);
    sessionStorage.setItem('userRole', role);
    sessionStorage.setItem('userName', userData.name);
  };

  const logout = () => {
    setUser(null);
    sessionStorage.removeItem('userRole');
    sessionStorage.removeItem('userName');
  };

  return (
    <AuthContext.Provider value={{
      user,
      login,
      logout,
      isAuthenticated: !!user
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
