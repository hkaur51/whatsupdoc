import { useCallback, useMemo, useState } from "react";
import Navbar from "./components/Navbar.jsx";
import DentalCalculator from "./components/DentalCalculator.jsx";
import ChatWidget from "./components/ChatWidget.jsx";
import AuthModal from "./components/AuthModal.jsx";
import { useAuth } from "./lib/auth.jsx";

const CLINIC_WA = import.meta.env.VITE_CLINIC_WA_NUMBER || "";

export default function App() {
  const { token } = useAuth();
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState("signin");
  const [ctx, setCtx] = useState({ state: "", insurance: "", total: 0, procedures: [] });

  const onContextChange = useCallback((c) => setCtx(c), []);
  const openSignin = () => { setAuthMode("signin"); setAuthOpen(true); };
  const openSignup = () => { setAuthMode("signup"); setAuthOpen(true); };

  const waHref = useMemo(() => {
    const lines = ["Hi! I'd like to book a dental appointment."];
    if (ctx.procedures?.length) lines.push("Procedures: " + ctx.procedures.join(", "));
    if (ctx.state) lines.push("State: " + ctx.state);
    if (typeof ctx.total === "number" && ctx.total > 0) lines.push("Estimated out-of-pocket: $" + ctx.total.toLocaleString());
    const text = encodeURIComponent(lines.join("\n"));
    return CLINIC_WA ? `https://wa.me/${CLINIC_WA}?text=${text}` : `https://wa.me/?text=${text}`;
  }, [ctx]);

  return (
    <div className="min-h-screen">
      <Navbar onOpenAuth={openSignin} />
      <main>
        <DentalCalculator onContextChange={onContextChange} />
        <div className="max-w-[560px] mx-auto px-6 pb-24 -mt-4">
          <div className="bg-white/70 backdrop-blur border border-[#e8dfd3] rounded-2xl p-5 flex flex-col sm:flex-row gap-3 shadow-sm">
            <button onClick={token ? undefined : openSignup}
              className="flex-1 bg-plum-900 text-white rounded-full py-3 px-5 font-mono text-[12px] tracking-wider uppercase hover:opacity-95"
              title={token ? "Open the chat below" : "Sign up to chat for free"}>
              {token ? "Chat is open below →" : "Sign up · Chat free with AI"}
            </button>
            <a href={waHref} target="_blank" rel="noopener"
              className="flex-1 bg-wa text-[#0b2b14] rounded-full py-3 px-5 font-mono text-[12px] tracking-wider uppercase hover:opacity-95 text-center">
              Chat on WhatsApp
            </a>
          </div>
          <p className="text-center font-mono text-[11px] text-plum-500 mt-3">
            Your selections and estimate are shared with the assistant.
          </p>
        </div>
      </main>
      <ChatWidget context={ctx} onRequireAuth={openSignin} />
      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} initialMode={authMode} />
    </div>
  );
}
