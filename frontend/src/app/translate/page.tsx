"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRightLeft, ClipboardCopy, Globe2, History, Languages, LayoutDashboard, LogOut, Mic2, ShieldCheck, UserRound } from "lucide-react";
import { authenticatedMutation, isAuthenticationError } from "@/lib/auth";
import { useRequiredSession } from "@/lib/use-session";

const LANGUAGES = [
  { code: "auto", label: "Detect language" },
  { code: "en", label: "English" },
  { code: "fr", label: "French" },
  { code: "es", label: "Spanish" },
  { code: "de", label: "German" },
  { code: "pt", label: "Portuguese" },
  { code: "ar", label: "Arabic" },
  { code: "wo", label: "Wolof" },
] as const;
const MAX_CHARS = 5000;
const languageName = (code: string) => LANGUAGES.find(lang => lang.code === code)?.label ?? code;
type SessionCreated = { session_id: string; agent_name: string; target_language: string };
type TranslationResult = { request_id: string; agent: string; original_text: string; translated_text: string };

export default function TranslatePage() {
  const router = useRouter();
  const { auth, status, message, retry } = useRequiredSession();
  const [sourceLanguage, setSourceLanguage] = useState("auto");
  const [targetLanguage, setTargetLanguage] = useState("en");
  const [sourceText, setSourceText] = useState("");
  const [resultText, setResultText] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  function swapLanguages() {
    if (sourceLanguage === "auto") return;
    setSourceLanguage(targetLanguage);
    setTargetLanguage(sourceLanguage);
    setResultText("");
    setCopied(false);
    setSessionId(null);
  }

  function reset() {
    setSourceText("");
    setResultText("");
    setError("");
    setCopied(false);
    setSessionId(null);
  }

  async function copyResult() {
    if (!resultText) return;
    try {
      await navigator.clipboard.writeText(resultText);
      setCopied(true);
    } catch {
      setError("Could not copy the translated text.");
    }
  }

  async function translate() {
    if (!auth || busy || !sourceText.trim() || sourceText.length > MAX_CHARS) return;
    setBusy(true);
    setError("");
    setCopied(false);
    setResultText("");
    try {
      // One authenticated translation session per active language pair / editor context.
      let activeSessionId = sessionId;
      if (!activeSessionId) {
        const created = await authenticatedMutation<SessionCreated>("/user/sessions", auth, {
          method: "POST",
          body: JSON.stringify({
            agent_type: "translation", execution_mode: "standard",
            source_language: sourceLanguage === "auto" ? "auto" : languageName(sourceLanguage),
            target_language: languageName(targetLanguage),
          }),
        });
        activeSessionId = created.session_id;
        setSessionId(activeSessionId);
      }
      const result = await authenticatedMutation<TranslationResult>("/user/translate/text", auth, {
        method: "POST",
        body: JSON.stringify({
          session_id: activeSessionId,
          text: sourceText,
          source_language: sourceLanguage === "auto" ? null : languageName(sourceLanguage),
          target_language: languageName(targetLanguage),
        }),
      });
      setResultText(result.translated_text);
    } catch (err) {
      if (isAuthenticationError(err)) { router.replace("/login"); return; }
      setError(err instanceof Error ? err.message : "Translation failed. Please try again.");
    } finally { setBusy(false); }
  }

  async function logout() {
    if (!auth) return;
    try {
      await authenticatedMutation("/auth/logout", auth, { method: "POST" });
      router.replace("/login");
    } catch (err) {
      if (isAuthenticationError(err)) { router.replace("/login"); return; }
      setError(err instanceof Error ? err.message : "Unable to sign out.");
    }
  }

  if (status === "error") return <main className="loading" role="alert"><div><p>Unable to verify your session: {message}</p><button className="primary" onClick={retry}>Try again</button></div></main>;
  if (!auth) return <main className="loading">Verifying your session…</main>;

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand dark-brand"><span className="brand-mark"><Globe2 size={23}/></span> WAAXALMA</div>
      <div className="sidebar-label">WORKSPACE</div>
      <nav aria-label="Main navigation">
        <Link href="/dashboard"><LayoutDashboard size={18}/> Dashboard</Link>
        <Link href="/translate" className="nav-active" aria-current="page"><Languages size={18}/> Translate</Link>
        <span className="nav-disabled"><Mic2 size={18}/> Interpreter <small>Soon</small></span>
        <Link href="/sessions"><History size={18}/> My Sessions</Link>
      </nav>
      <div className="sidebar-bottom">
        <div className="sidebar-note"><ShieldCheck size={18}/><strong>Private workspace</strong><span>Text remains in this browser until you submit a translation.</span></div>
        <button className="logout" onClick={logout}><LogOut size={17}/> Sign out</button>
      </div>
    </aside>
    <main className="main-panel">
      <header className="topbar"><div className="breadcrumb">Workspace <span>/</span> <strong>Translate</strong></div><div className="profile"><span className="avatar"><UserRound size={17}/></span><span>{auth.user.email}</span></div></header>
      <div className="dashboard-content">
        <div className="welcome"><div><span className="eyebrow">TEXT TRANSLATION</span><h1>Translate<span className="period">.</span></h1><p>Prepare a translation across languages.</p></div><span className="translate-stage-label">Connected to Waaxalma Translation Agent</span></div>
        <section className="translate-workspace" aria-label="Translation editor">
          <div className="translate-toolbar">
            <label htmlFor="source-language">From</label>
            <select id="source-language" value={sourceLanguage} disabled={busy} onChange={e => {setSourceLanguage(e.target.value);setResultText("");setSessionId(null);}}>
              {LANGUAGES.map(language => <option value={language.code} key={language.code}>{language.label}</option>)}
            </select>
            <button className="translate-swap" onClick={swapLanguages} disabled={busy || sourceLanguage === "auto"} title="Swap languages" aria-label="Swap source and target languages"><ArrowRightLeft size={18}/></button>
            <label htmlFor="target-language">To</label>
            <select id="target-language" value={targetLanguage} disabled={busy} onChange={e => {setTargetLanguage(e.target.value);setResultText("");setSessionId(null);}}>
              {LANGUAGES.filter(language => language.code !== "auto").map(language => <option value={language.code} key={language.code}>{language.label}</option>)}
            </select>
          </div>
          <div className="translate-columns">
            <div className="translate-panel">
              <label htmlFor="translation-source" className="translate-panel-label">Source text</label>
              <textarea id="translation-source" value={sourceText} maxLength={MAX_CHARS} disabled={busy} onChange={e => {setSourceText(e.target.value);setResultText("");setCopied(false);}} placeholder="Enter text to translate…" />
              <div className="translate-panel-footer"><span>{sourceText.length.toLocaleString()} / {MAX_CHARS.toLocaleString()} characters</span><button className="translate-text-button" onClick={reset} disabled={busy || (!sourceText && !resultText)}>Clear</button></div>
            </div>
            <div className="translate-panel translate-result">
              <span className="translate-panel-label">Translation</span>
              <div className="translate-output" aria-live="polite">{resultText || <span className="translate-placeholder">Your translated text will appear here.</span>}</div>
              <div className="translate-panel-footer"><span>{resultText ? "Ready" : "Awaiting translation"}</span><button className="translate-text-button" onClick={() => void copyResult()} disabled={!resultText}><ClipboardCopy size={15}/>{copied ? "Copied" : "Copy"}</button></div>
            </div>
          </div>
          <div className="translate-actions">
            <p>{sessionId ? `Session: ${sessionId}` : "A private translation session will be created on first use."}</p>
            <button className="primary" type="button" onClick={() => void translate()} disabled={busy || !sourceText.trim() || sourceText.length > MAX_CHARS}>{busy ? "Translating…" : "Translate text"}</button>
          </div>
        </section>
        {error && <p role="alert" className="error">{error}</p>}
      </div>
    </main>
  </div>;
}
