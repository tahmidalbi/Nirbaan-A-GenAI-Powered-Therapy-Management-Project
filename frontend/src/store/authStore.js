import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      token: null,
      _hasHydrated: false,

      setHasHydrated: (state) => {
        set({
          _hasHydrated: state
        });
      },

      login: (userData, token) => {
        console.log('[AUTH STORE] Login called with:', { userData, token });
        const newState = {
          user: userData,
          token: token,
          isAuthenticated: true,
        };
        set(newState);
        console.log('[AUTH STORE] State updated');
      },

      logout: () => {
        console.log('[AUTH STORE] Logout called');
        set({
          user: null,
          token: null,
          isAuthenticated: false,
        });
      },

      updateUser: (userData) => {
        console.log('[AUTH STORE] Update user called with:', userData);
        set({ user: userData });
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      onRehydrateStorage: () => (state) => {
        console.log('[AUTH STORE] Rehydration complete');
        state?.setHasHydrated(true);
      },
    }
  )
);