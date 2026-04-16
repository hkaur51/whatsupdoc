import { useMemo, useState } from "react";
import { Plus, Minus } from "lucide-react";
import {
  CATS, PROCS, CAT_RANGES, TIERS, INS_KEYS, INS_RATES, INS_HAS_MAX, INS_DEF_MAX, TIER_IDX,
  MS, MC, SM, TL, TC, STATES, catOfProc,
} from "../data/calculator.js";

export default function DentalCalculator({ onContextChange }) {
  const [st, setSt] = useState("Texas");
  const [ins, setIns] = useState("No insurance");
  const [aMax, setAMax] = useState(INS_DEF_MAX.PPO);
  const [ded, setDed] = useState(50);
  const [sel, setSel] = useState({}); // { [procIndex]: qty }
  const [openCat, setOpenCat] = useState(-1);
  const [showMap, setShowMap] = useState(false);
  const [showSrc, setShowSrc] = useState(false);

  const mult = SM[st] || 1;
  const plan = INS_RATES[ins];
  const mcd = ins === "Medicaid" ? MS[st] : null;

  const { items, tR, tC, tP, warnMsg, contextProcs } = useMemo(() => {
    const items = [];
    for (const pi of Object.keys(sel).map(Number)) {
      const p = PROCS[pi];
      const ci = catOfProc(pi);
      const qty = sel[pi];
      const mid = Math.round(p[2] * mult * qty);
      let cov = 0, pay = mid;
      if (ins === "Medicaid" && mcd) {
        if (MC[mcd[0]][ci] && p[4] > 0) { cov = Math.round(p[4] * qty); pay = 0; }
      } else {
        const ti = TIER_IDX[TIERS[ci]];
        const r = plan[ti] || 0;
        cov = Math.round(mid * r);
        pay = mid - cov;
      }
      items.push({ pi, ci, name: p[0], qty, mid, cov, pay });
    }
    let tR = 0, tC = 0, tP = 0;
    for (const r of items) { tR += r.mid; tC += r.cov; tP += r.pay; }
    if (INS_HAS_MAX[ins]) { tP += ded; tC = Math.max(0, tC - ded); }
    const cap = INS_HAS_MAX[ins] ? aMax : (mcd && mcd[1] ? mcd[1] : 0);
    let warnMsg = "";
    if (cap && tC > cap) {
      const ov = tC - cap;
      tP += ov; tC = cap;
      warnMsg = `Exceeds $${cap.toLocaleString()} annual cap — +$${ov.toLocaleString()} out of pocket.`;
    }
    return { items, tR, tC, tP, warnMsg, contextProcs: items.map((r) => r.name) };
  }, [sel, st, ins, aMax, ded, mult, plan, mcd]);

  // Surface the context upward so the ChatWidget can pass it to the bot.
  useMemo(() => {
    onContextChange?.({ state: st, insurance: ins, total: tP, procedures: contextProcs });
  }, [st, ins, tP, contextProcs, onContextChange]);

  const toggleProc = (pi) =>
    setSel((s) => { const n = { ...s }; if (n[pi]) delete n[pi]; else n[pi] = 1; return n; });
  const setQty = (pi, delta) =>
    setSel((s) => {
      if (!s[pi]) return s;
      const next = Math.max(1, Math.min(10, s[pi] + delta));
      return { ...s, [pi]: next };
    });

  return (
    <div className="max-w-[560px] mx-auto px-6 pb-16">
      <header className="pt-16 pb-10">
        <p className="tag">dental cost estimator</p>
        <h1 className="mt-4 text-[40px] leading-[1.1] tracking-tight text-plum-900 font-normal">
          How much will your<br />dentist visit cost?
        </h1>
        <p className="mt-4 text-[16px] leading-relaxed text-plum-700 max-w-[420px]">
          Pick your state, insurance, and procedures.<br />Get a realistic range before you call.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-5 mb-12">
        <div>
          <label className="tag block mb-2">State</label>
          <select className="fi" value={st} onChange={(e) => setSt(e.target.value)}>
            {STATES.map((s) => <option key={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="tag block mb-2">Insurance</label>
          <select className="fi" value={ins} onChange={(e) => setIns(e.target.value)}>
            {INS_KEYS.map((k) => <option key={k}>{k}</option>)}
          </select>
        </div>
      </div>

      {mcd && (
        <div className="mb-10 pb-5 border-b border-[#ddd5cc]">
          <span className="inline-block w-[7px] h-[7px] rounded-full align-middle mr-2.5" style={{ background: TC[mcd[0]] }} />
          <span className="font-mono text-sm text-plum-900">{TL[mcd[0]]}</span>
          <span className="text-[13px] text-[#b8a9c4] ml-2">&mdash; {mcd[2]}</span>
          {mcd[0] === "eo" && (
            <div className="text-[13px] text-[#c2340a] mt-2 italic">
              Only emergency extractions covered in {st}.
            </div>
          )}
        </div>
      )}

      {INS_HAS_MAX[ins] && (
        <div className="grid grid-cols-2 gap-5 mb-10">
          <div>
            <label className="tag block mb-2">Annual max ($)</label>
            <input type="number" className="fi" value={aMax} onChange={(e) => setAMax(+e.target.value || 0)} />
          </div>
          <div>
            <label className="tag block mb-2">Deductible ($)</label>
            <input type="number" className="fi" value={ded} onChange={(e) => setDed(+e.target.value || 0)} />
          </div>
        </div>
      )}

      <p className="tag mb-4">procedures</p>
      {CATS.map((cat, c) => {
        const isO = openCat === c;
        const isMcd = !!(ins === "Medicaid" && mcd);
        const catOk = isMcd ? MC[mcd[0]][c] : 1;
        let cnt = 0;
        for (let pi = CAT_RANGES[c][0]; pi <= CAT_RANGES[c][1]; pi++) if (sel[pi]) cnt++;
        return (
          <div key={cat} className="border-t border-[#ddd5cc]">
            <button
              onClick={() => setOpenCat(isO ? -1 : c)}
              className="w-full flex justify-between items-center py-5 text-left font-medium text-[17px] text-ink"
            >
              <span>
                {cat}
                {cnt > 0 && (
                  <span className="ml-2.5 font-mono text-[10px] bg-plum-900 text-white rounded-full px-2 py-[3px]">
                    {cnt}
                  </span>
                )}
                {isMcd && !catOk && <span className="ml-2.5 font-mono text-[11px] text-red-700">not covered</span>}
              </span>
              <span className={`text-[20px] text-[#9a8aaa] transition-transform ${isO ? "rotate-45" : ""}`}>+</span>
            </button>
            {isO && (
              <div className="pb-5">
                {Array.from({ length: CAT_RANGES[c][1] - CAT_RANGES[c][0] + 1 }, (_, k) => {
                  const pi = CAT_RANGES[c][0] + k;
                  const p = PROCS[pi];
                  const on = !!sel[pi];
                  const adj = Math.round(p[2] * mult);
                  return (
                    <div
                      key={pi}
                      onClick={() => { if (!on) toggleProc(pi); }}
                      className="flex items-center gap-4 py-3 cursor-pointer border-t border-[#e8e0d8]"
                    >
                      <button
                        onClick={(e) => { e.stopPropagation(); toggleProc(pi); }}
                        className={`w-[18px] h-[18px] rounded-sm relative flex-shrink-0 ${on ? "bg-plum-900" : "border-2 border-[#9a8aaa]"}`}
                        aria-label={on ? "deselect" : "select"}
                      >
                        {on && (
                          <span className="absolute left-[4px] top-[2px] w-[5px] h-[9px] border-r-2 border-b-2 border-white rotate-45 block" />
                        )}
                      </button>
                      <span className={`flex-1 text-[15px] ${on ? "text-ink font-medium" : "text-plum-700"}`}>{p[0]}</span>
                      <span className="font-mono text-[13px] text-plum-500 flex-shrink-0">${adj}</span>
                      {on && (
                        <div className="flex items-center gap-2 ml-1">
                          <button onClick={(e) => { e.stopPropagation(); setQty(pi, -1); }}
                            className="w-6 h-6 rounded-full border-2 border-[#9a8aaa] text-plum-900 font-mono text-[14px] flex items-center justify-center">
                            <Minus size={12} />
                          </button>
                          <span className="font-mono text-[14px] min-w-[14px] text-center">{sel[pi]}</span>
                          <button onClick={(e) => { e.stopPropagation(); setQty(pi, 1); }}
                            className="w-6 h-6 rounded-full border-2 border-[#9a8aaa] text-plum-900 font-mono text-[14px] flex items-center justify-center">
                            <Plus size={12} />
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
      <div className="border-t border-[#ddd5cc]" />

      {items.length > 0 ? (
        <section className="mt-14">
          <p className="tag mb-6">your estimate</p>
          {items.map((r) => (
            <div key={r.pi} className="flex justify-between items-baseline py-3 border-b border-[#e8e0d8]">
              <span className="text-[15px] text-ink flex-1">
                {r.name}
                {r.qty > 1 && <span className="text-[#d0c4d8] ml-1.5 text-[12px]">×{r.qty}</span>}
              </span>
              <span className="font-mono text-[14px] text-right">
                {r.cov > 0 ? (
                  <>
                    <span className="text-[#9a8aaa] line-through mr-3">${r.mid.toLocaleString()}</span>
                    <span className="text-plum-900 font-semibold">${r.pay.toLocaleString()}</span>
                  </>
                ) : (
                  <span className="text-plum-700 font-medium">${r.pay.toLocaleString()}</span>
                )}
              </span>
            </div>
          ))}
          {warnMsg && <div className="text-[14px] text-[#b45309] mt-4 italic">{warnMsg}</div>}
          <div className="mt-12 pt-7 border-t-[3px] border-plum-900">
            <div className="flex justify-between mb-2 text-sm">
              <span className="text-plum-700 font-medium">Retail</span>
              <span className="font-mono text-plum-700">${tR.toLocaleString()}</span>
            </div>
            {tC > 0 && (
              <div className="flex justify-between mb-2 text-sm">
                <span className="text-[#16763a] font-medium">Covered</span>
                <span className="font-mono text-[#16763a]">−${tC.toLocaleString()}</span>
              </div>
            )}
            <div className="flex justify-between items-baseline mt-5">
              <span className="text-[18px] text-plum-900 font-medium">You pay</span>
              <span className="font-mono text-[38px] tracking-tight text-[#c2185b]">
                ${tP.toLocaleString()}
              </span>
            </div>
            {tR > 0 && tC > 0 && (
              <div className="font-mono text-[12px] text-plum-500 text-right mt-1.5">
                saving {Math.round((tC / tR) * 100)}%
              </div>
            )}
          </div>
        </section>
      ) : (
        <p className="text-center text-[#9a8aaa] text-[16px] py-14 italic">Select procedures above to see your estimate.</p>
      )}

      {ins === "Medicaid" && (
        <div className="mt-12">
          <button className="font-mono text-[13px] text-plum-700 underline underline-offset-[3px] decoration-plum-300"
            onClick={() => setShowMap((x) => !x)}>
            {showMap ? "hide" : "view"} all 50 states →
          </button>
          {showMap && (
            <div className="mt-4 max-h-[340px] overflow-y-auto scrollbar-thin">
              {Object.keys(MS).sort().map((s) => {
                const info = MS[s];
                return (
                  <div key={s} className={`flex items-center gap-2.5 py-2 border-b border-[#e8e0d8] text-sm ${s === st ? "bg-plum-100 rounded-sm px-1.5" : ""}`}>
                    <span className="w-[7px] h-[7px] rounded-full flex-shrink-0" style={{ background: TC[info[0]] }} />
                    <span className={`w-[140px] flex-shrink-0 ${s === st ? "font-medium" : ""}`}>{s}</span>
                    <span className="font-mono text-[12px] text-plum-700 flex-1">{TL[info[0]]}</span>
                    <span className="font-mono text-[12px] text-plum-500">{info[1] ? `$${info[1]}` : "—"}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      <div className="mt-14 pt-6 border-t border-[#e8e0d8]">
        <button className="font-mono text-[13px] text-plum-700 underline underline-offset-[3px] decoration-plum-300"
          onClick={() => setShowSrc((x) => !x)}>
          {showSrc ? "hide" : "view"} data sources →
        </button>
        {showSrc && (
          <div className="mt-4 font-mono text-[12px] leading-loose text-plum-700 space-y-1.5">
            <p><b className="text-plum-900">Pricing</b> CareCredit/Synchrony 2024 · ADA Fee Survey · Fair Health · MD Medicaid 2025</p>
            <p><b className="text-plum-900">Medicaid</b> CareQuest 2025 · MACPAC · ADA state schedules (Sep 2025)</p>
            <p><b className="text-plum-900">Geographic</b> NDAS multipliers · Fair Health geozip</p>
            <p><b className="text-plum-900">Insurance</b> ADA/NADP benefit design surveys</p>
            <p className="italic mt-2">Estimates only. Not financial or medical advice.</p>
          </div>
        )}
      </div>

      <p className="text-center font-mono text-[11px] text-[#9a8aaa] mt-16">dental cost estimator · 2026</p>
    </div>
  );
}
