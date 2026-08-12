import { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { authApi } from '../lib/api';

const inputClass =
  'w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500';

function RequestResetForm() {
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await authApi.forgotPassword({ email });
    } finally {
      setSubmitting(false);
      // Always show the generic confirmation — the API itself never reveals
      // whether the email exists, so neither should the UI.
      setSent(true);
    }
  };

  if (sent) {
    return (
      <div className="space-y-3 text-center">
        <p className="text-sm text-foreground">
          If that email is registered, a password reset link has been sent.
        </p>
        <Link to="/login" className="text-sm text-brand-600 hover:underline">
          Back to log in
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label className="block text-sm font-medium text-foreground mb-1">Email</label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={inputClass}
          required
          autoFocus
        />
      </div>
      <button
        type="submit"
        disabled={submitting}
        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium transition-colors"
      >
        {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
        Send reset link
      </button>
      <Link to="/login" className="block text-center text-sm text-muted-foreground hover:text-foreground">
        Back to log in
      </Link>
    </form>
  );
}

function ConfirmResetForm({ token }: { token: string }) {
  const navigate = useNavigate();
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    setSubmitting(true);
    try {
      await authApi.resetPassword({ token, new_password: newPassword });
      navigate('/login', { replace: true });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label className="block text-sm font-medium text-foreground mb-1">New password</label>
        <input
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          className={inputClass}
          minLength={8}
          required
          autoFocus
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-foreground mb-1">Confirm new password</label>
        <input
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          className={inputClass}
          minLength={8}
          required
        />
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium transition-colors"
      >
        {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
        Reset password
      </button>
    </form>
  );
}

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background px-4 py-8">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <img src="/logo.png" alt="MyACE" className="h-[60px] w-[60px] sm:h-16 sm:w-16" />
          <h1 className="text-xl font-bold text-foreground">
            {token ? 'Choose a new password' : 'Reset your password'}
          </h1>
        </div>

        <div className="bg-card rounded-xl border border-border p-6">
          {token ? <ConfirmResetForm token={token} /> : <RequestResetForm />}
        </div>
      </div>
    </div>
  );
}
