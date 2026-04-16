import { useEffect, useRef, useState } from "react";
import { MessageCircle, X, Send, Lock } from "lucide-react";
import { api } from "../lib/api.js";
import { useAuth } from "../lib/auth.jsx";

const QUICK = [
  "I'd like to book a cleaning tomorrow morning",
  "When are you available this week?",
  "Check my appointments",
];

export default function ChatWidget({ context, onRequireAuth }) {
  const { token, user } = useAuth();
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [firstSend, setFirstSend] = useState(true);
  const bodyRef = useRef(null);

  // Reset transcript when the user changes (login/logout).
  useEffect(() => { setMsgs([]); setFirstSend(true); }, [user?.id]);

  useEffect(() => {
    if (open && bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [msgs, open, busy]);

  const handleFabClick = () => {
    if (!token) { onRequireAuth?.(); return; }
    setOpen((o) => {
      const next = !o;
      if (next && msgs.length === 0) {
        setMsgs([{
          role: "bot",
          text: `Hi ${user?.name?.split(" ")[0] || "there"}! I'm your dental booking assistant. Tell me what you'd like to book, reschedule, or check.`,
        }]);
      }
      return next;
    });
  };

  async function send(text) {
    const msg = (text ?? input).trim();
    if (!msg || busy) return;
    if (!token) { onRequireAuth?.(); return; }
    setMsgs((m) => [...m, { role: "me", text: msg }]);
    setInput("");
    setBusy(true);
    try {
      const payload = { message: msg };
      if (firstSend && context && (context.procedures?.length || context.total)) {
        payload.context = context;
      }
      const res = await api("/chat", { method: "POST", body: payload, token });
      setFirstSend(false);
      const replies = res.replies?.length ? res.replies : ["(no reply)"];
      setMsgs((m) => [...m, ...replies.map((t) => ({ role: "bot", text: t }))]);
    } catch (err) {
      setMsgs((m) => [...m, { role: "bot", text: `⚠️  ${err.message || "Network error"}` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button onClick={handleFabClick}
        aria-label="Open booking assistant"
        className="fixed right-6 bottom-6 w-[60px] h-[60px] rounded-full bg-plum-900 text-white shadow-[0_12px_32px_rgba(61,29,92,0.35)] hover:scale-105 transition-transform z-40 flex items-center justify-center">
        {open ? <X size={22} /> : <MessageCircle size={24} />}
      </button>

      {open && (
        <div className="fixed right-6 bottom-24 w-[380px] max-w-[calc(100vw-32px)] h-[560px] max-h-[calc(100vh-120px)] bg-white rounded-2xl shadow-[0_24px_60px_rgba(20,10,40,0.22)] z-50 flex flex-col overflow-hidden animate-[fadein_.25s_ease]">
          <div className="px-5 py-4 bg-plum-900 text-white flex items-center gap-3">
            <span className="w-2.5 h-2.5 rounded-full bg-wa shadow-[0_0_0_3px_rgba(37,211,102,0.25)]" />
            <div>
              <h3 className="text-[17px] leading-tight">Dental Booking Assistant</h3>
              <small className="font-mono text-[10px] tracking-[0.1em] uppercase opacity-70">
                DSPy + Gemini · free for members
              </small>
            </div>
            <button onClick={() => setOpen(false)} className="ml-auto opacity-70 hover:opacity-100">
              <X size={20} />
            </button>
          </div>

          {!token ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-3 bg-[#FAF7F3] px-6 text-center">
              <Lock size={28} className="text-plum-500" />
              <p className="text-plum-900">Sign in to start chatting.</p>
              <p className="text-[13px] text-plum-700">Free, unlimited access to the assistant once you have an account.</p>
              <button onClick={onRequireAuth}
                className="mt-2 bg-plum-900 text-white rounded-full py-2.5 px-5 font-mono text-[12px] tracking-wider uppercase">
                Sign in / Sign up
              </button>
            </div>
          ) : (
            <>
              <div ref={bodyRef} className="flex-1 overflow-y-auto bg-[#FAF7F3] p-4 flex flex-col gap-2.5 scrollbar-thin">
                {msgs.map((m, i) => (
                  <div key={i}
                    className={`max-w-[85%] px-3.5 py-2.5 rounded-2xl text-[14.5px] leading-relaxed whitespace-pre-wrap break-words ${
                      m.role === "me"
                        ? "self-end bg-plum-900 text-white rounded-br-[4px]"
                        : "self-start bg-white text-ink border border-[#ece4d8] rounded-bl-[4px]"
                    }`}>
                    {m.text}
                  </div>
                ))}
                {busy && <div className="self-start text-plum-500 italic text-[13px] px-2">assistant is typing...</div>}
              </div>

              <div className="flex flex-wrap gap-1.5 px-4 pb-2 bg-[#FAF7F3]">
                {QUICK.map((q) => (
                  <button key={q} onClick={() => send(q)}
                    className="border border-[#d8cfc2] bg-white rounded-full px-3 py-1 font-mono text-[11px] text-plum-900 hover:bg-plum-900 hover:text-white transition-colors">
                    {q}
                  </button>
                ))}
              </div>

              <form onSubmit={(e) => { e.preventDefault(); send(); }}
                className="flex gap-2 p-3 border-t border-[#ece4d8] bg-white">
                <input autoFocus value={input} onChange={(e) => setInput(e.target.value)}
                  placeholder="Tell me what you need..."
                  className="flex-1 px-3.5 py-3 border border-[#d8cfc2] rounded-full text-[15px] outline-none focus:border-plum-900" />
                <button type="submit" disabled={busy || !input.trim()}
                  className="bg-plum-900 text-white rounded-full w-11 h-11 flex items-center justify-center disabled:opacity-40">
                  <Send size={16} />
                </button>
              </form>
            </>
          )}
        </div>
      )}

      <style>{`@keyframes fadein { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }`}</style>
    </>
  );
}
