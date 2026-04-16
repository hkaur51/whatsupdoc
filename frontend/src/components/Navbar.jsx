import { useState } from "react";
import { LogIn, LogOut, User } from "lucide-react";
import { useAuth } from "../lib/auth.jsx";

export default function Navbar({ onOpenAuth }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-30 backdrop-blur bg-[rgba(245,240,235,0.85)] border-b border-[#e8dfd3]">
      <div className="max-w-[960px] mx-auto px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-wa inline-block" />
          <span className="font-mono text-[11px] tracking-[0.18em] uppercase text-plum-900">
            WhatsUpDoc
          </span>
        </div>
        {user ? (
          <div className="relative">
            <button onClick={() => setOpen((x) => !x)}
              className="flex items-center gap-2 font-mono text-[12px] text-plum-900 hover:bg-plum-100 rounded-full py-1.5 px-3">
              <User size={14} /> {user.name || user.email}
            </button>
            {open && (
              <div className="absolute right-0 mt-2 w-44 bg-white border border-[#e8dfd3] rounded-xl shadow-lg py-1 text-sm">
                <button className="w-full text-left px-4 py-2 hover:bg-plum-50 flex items-center gap-2"
                  onClick={() => { setOpen(false); logout(); }}>
                  <LogOut size={14} /> Sign out
                </button>
              </div>
            )}
          </div>
        ) : (
          <button onClick={onOpenAuth}
            className="flex items-center gap-2 bg-plum-900 text-white rounded-full py-1.5 px-4 font-mono text-[12px] tracking-wider uppercase hover:opacity-90">
            <LogIn size={14} /> Sign in
          </button>
        )}
      </div>
    </header>
  );
}
