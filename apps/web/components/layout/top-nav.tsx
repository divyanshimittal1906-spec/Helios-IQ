'use client';

import { useEffect, useState } from 'react';
import { Bell, KeyRound, LogIn, LogOut, Menu, Search, UserPlus, X } from 'lucide-react';
import { getCurrentUser, loginUser, logoutUser, registerUser, type UserRead } from '@/lib/api';
import { useLayout } from './layout-context';

export function TopNav() {
  const { toggleSidebar } = useLayout();
  const [user, setUser] = useState<UserRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function checkCurrentUser() {
    try {
      setLoading(true);
      const current = await getCurrentUser();
      setUser(current);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void checkCurrentUser();

    const handleAuthEvent = (e: Event) => {
      const custom = e as CustomEvent<UserRead | null>;
      if (custom.detail) {
        setUser(custom.detail);
      } else {
        void checkCurrentUser();
      }
    };

    window.addEventListener('helios-auth-change', handleAuthEvent);
    return () => {
      window.removeEventListener('helios-auth-change', handleAuthEvent);
    };
  }, []);

  async function handleAuthSubmit(e: React.FormEvent) {
    e.preventDefault();
    setAuthError(null);

    const cleanEmail = email.trim();
    const cleanPassword = password;
    const cleanFullName = fullName.trim();

    if (!cleanEmail) {
      setAuthError('Email address is required.');
      return;
    }

    if (!cleanPassword) {
      setAuthError('Password is required.');
      return;
    }

    if (isRegister) {
      if (!cleanFullName) {
        setAuthError('Full name is required to create an account.');
        return;
      }
      if (cleanPassword.length < 8) {
        setAuthError('Password must be at least 8 characters long.');
        return;
      }
    }

    setSubmitting(true);
    try {
      if (isRegister) {
        await registerUser({ email: cleanEmail, password: cleanPassword, full_name: cleanFullName });
        const res = await loginUser({ email: cleanEmail, password: cleanPassword });
        setUser(res.user);
      } else {
        const res = await loginUser({ email: cleanEmail, password: cleanPassword });
        setUser(res.user);
      }
      setModalOpen(false);
      setEmail('');
      setPassword('');
      setFullName('');
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : 'Authentication failed.');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleQuickDemoLogin() {
    setAuthError(null);
    setSubmitting(true);
    setEmail('user@example.com');
    setPassword('devpassword123');
    try {
      const res = await loginUser({ email: 'user@example.com', password: 'devpassword123' });
      setUser(res.user);
      setModalOpen(false);
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : 'Demo login failed.');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleLogout() {
    try {
      await logoutUser();
    } catch {
      // ignore
    } finally {
      setUser(null);
    }
  }

  return (
    <header className="sticky top-0 z-30 flex h-14 w-full items-center justify-between border-b border-slate-200/80 bg-white/95 px-4 backdrop-blur-xs sm:px-6">
      {/* Left: Mobile Toggle & Minimal Breadcrumb */}
      <div className="flex items-center gap-2.5">
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label="Toggle navigation menu"
          className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900 md:hidden"
        >
          <Menu size={18} />
        </button>

        <span className="text-xs font-medium text-slate-500 hidden sm:inline">Workspace</span>
        <span className="text-xs text-slate-300 hidden sm:inline">/</span>
        <span className="text-xs font-semibold text-slate-800">Enterprise</span>
      </div>

      {/* Middle: Clean Uncluttered Search */}
      <div className="hidden max-w-xs flex-1 px-4 md:block">
        <label className="flex items-center gap-2 rounded-lg border border-slate-200/80 bg-slate-50/70 px-2.5 py-1.5 text-slate-400 focus-within:border-blue-500 focus-within:bg-white focus-within:ring-1 focus-within:ring-blue-100">
          <Search size={13} className="text-slate-400" />
          <input
            aria-label="Search"
            placeholder="Search workspace..."
            className="w-full bg-transparent text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none"
          />
        </label>
      </div>

      {/* Right: Actions & Profile */}
      <div className="flex items-center gap-2">
        <button
          aria-label="Notifications"
          className="flex h-8 w-8 items-center justify-center rounded-md text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition"
        >
          <Bell size={15} />
        </button>

        {loading ? (
          <div className="h-8 w-24 animate-pulse rounded-md bg-slate-100" />
        ) : user ? (
          <div className="flex items-center gap-1.5">
            <div className="flex items-center gap-2 rounded-lg py-1 pl-1.5 pr-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-[10px] font-semibold text-white uppercase">
                {user.full_name ? user.full_name.charAt(0) : user.email.charAt(0)}
              </div>
              <div className="hidden text-left lg:block max-w-[120px]">
                <div id="current-user-name" className="text-xs font-medium text-slate-900 truncate leading-none">
                  {user.full_name || user.email}
                </div>
                <div id="current-user-email" className="text-[10px] text-slate-400 truncate mt-0.5 leading-none">
                  {user.email}
                </div>
              </div>
            </div>
            <button
              id="logout-btn"
              onClick={handleLogout}
              title="Log out"
              className="flex h-7 w-7 items-center justify-center rounded-md text-slate-400 hover:bg-rose-50 hover:text-rose-600 transition"
            >
              <LogOut size={14} />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <button
              id="quick-demo-btn"
              onClick={handleQuickDemoLogin}
              className="hidden sm:inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-900 px-2 py-1 transition"
            >
              <KeyRound size={12} />
              Demo Login
            </button>
            <button
              id="login-modal-btn"
              onClick={() => {
                setModalOpen(true);
                setIsRegister(false);
                setAuthError(null);
              }}
              className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-blue-700 shadow-xs"
            >
              <LogIn size={13} />
              Sign in
            </button>
          </div>
        )}
      </div>

      {/* Authentication Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3.5">
              <div className="flex items-center gap-2 text-slate-900">
                {isRegister ? (
                  <UserPlus size={18} className="text-blue-600" />
                ) : (
                  <LogIn size={18} className="text-blue-600" />
                )}
                <span className="font-semibold text-sm">
                  {isRegister ? 'Create Account' : 'Sign In'}
                </span>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
              >
                <X size={16} />
              </button>
            </div>

            {authError && (
              <div
                id="auth-error-message"
                className="mt-3.5 rounded-lg border border-rose-200 bg-rose-50 p-2.5 text-xs text-rose-700"
              >
                {authError}
              </div>
            )}

            <form onSubmit={handleAuthSubmit} noValidate className="mt-4 space-y-3">
              {isRegister && (
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Full Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="auth-fullname"
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Jane Doe"
                    className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-100"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Email Address <span className="text-rose-500">*</span>
                </label>
                <input
                  id="auth-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="user@example.com"
                  className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-100"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Password <span className="text-rose-500">*</span>
                </label>
                <input
                  id="auth-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-100"
                />
                {isRegister && (
                  <p className="mt-1 text-[11px] text-slate-400">Minimum 8 characters.</p>
                )}
              </div>

              <div className="pt-1">
                <button
                  id="auth-submit-btn"
                  type="submit"
                  disabled={submitting}
                  className="w-full rounded-lg bg-blue-600 py-2.5 text-xs font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50 shadow-xs"
                >
                  {submitting ? 'Authenticating...' : isRegister ? 'Create Account' : 'Sign In'}
                </button>
              </div>
            </form>

            <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-xs text-slate-500">
              <button
                id="toggle-auth-mode-btn"
                type="button"
                onClick={() => {
                  setIsRegister(!isRegister);
                  setAuthError(null);
                }}
                className="text-blue-600 hover:underline"
              >
                {isRegister ? 'Already registered? Sign in' : "New user? Register"}
              </button>
              <button
                id="demo-credentials-btn"
                type="button"
                onClick={handleQuickDemoLogin}
                className="text-slate-500 hover:text-slate-900 underline"
              >
                Use demo account
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
