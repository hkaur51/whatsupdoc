import { useState } from "react";
import { X, Loader2 } from "lucide-react";
import { useAuth } from "../lib/auth.jsx";

export default function AuthModal({ open, onClose, initialMode = "signin" }) {
  const { login, signup, loading } = useAuth();
  const [mode, setMode] = useState(initialMode);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  if (!open) return null;
  const isSignup = mode === "signup";

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      if (isSignup) await signup({ name, email, password });
      else await login({ email, password });
      onClose();
    } catch (err) {
      setError(err.message || "Something went wrong.");
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(20,10,40,0.45)] backdrop-blur-sm px-4"
      onClick={onClose}>
      <div className="bg-[#FAF7F3] w-full max-w-[420px] rounded-2xl shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}>
        <div className="px-7 pt-7 pb-2 flex items-start justify-between">
          <div>
            <p className="tag">{isSignup ? "create account" : "welcome back"}</p>
            <h2 className="mt-2 text-[26px] text-plum-900 font-normal leading-tight">
              {isSignup ? "Start booking in minutes" : "Sign in to chat"}
            </h2>
            <p className="mt-1 text-[13.5px] text-plum-700">
              Free unlimited chat with the AI dental booking assistant.
            </p>
          </div>
          <button onClick={onClose} className="text-plum-500 hover:text-plum-900 -mr-2"><X size={20} /></button>
        </div>
        <form onSubmit={submit} className="px-7 pb-7 pt-4 space-y-5">
          {isSignup && (
            <div>
              <label className="tag block mb-1.5">Name</label>
              <input className="fi" value={name} onChange={(e) => setName(e.target.value)} required minLength={2} />
            </div>
          )}
          <div>
            <label className="tag block mb-1.5">Email</label>
            <input type="email" className="fi" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div>
            <label className="tag block mb-1.5">Password</label>
            <input type="password" className="fi" value={password} onChange={(e) => setPassword(e.target.value)}
              required minLength={isSignup ? 8 : 1} />
            {isSignup && <p className="font-mono text-[10px] text-plum-500 mt-1.5">minimum 8 characters</p>}
          </div>
          {error && <div className="text-[13px] text-red-700 bg-red-50 border border-red-100 rounded-md px-3 py-2">{error}</div>}
          <button type="submit" disabled={loading}
            className="w-full bg-plum-900 text-white rounded-full py-3 font-mono text-[13px] tracking-wider uppercase flex items-center justify-center gap-2 hover:opacity-95 disabled:opacity-60">
            {loading && <Loader2 size={14} className="animate-spin" />}
            {isSignup ? "Create account" : "Sign in"}
          </button>
          <p className="text-center text-[13px] text-plum-700">
            {isSignup ? "Already have an account?" : "Don't have an account?"}{" "}
            <button type="button" onClick={() => setMode(isSignup ? "signin" : "signup")}
              className="text-plum-900 underline decoration-plum-300 underline-offset-[3px] font-medium">
              {isSignup ? "Sign in" : "Sign up — it's free"}
            </button>
          </p>
        </form>
      </div>
    </div>
  );
}
