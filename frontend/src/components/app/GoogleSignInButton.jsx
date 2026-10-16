import { useEffect, useRef } from "react";

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const GSI_SRC = "https://accounts.google.com/gsi/client";

let scriptPromise = null;
function loadGsi() {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (!scriptPromise) {
    scriptPromise = new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = GSI_SRC;
      s.async = true;
      s.defer = true;
      s.onload = () => resolve();
      s.onerror = () => {
        scriptPromise = null;
        reject(new Error("gsi load failed"));
      };
      document.head.appendChild(s);
    });
  }
  return scriptPromise;
}

/** "Sign in with Google" button. Renders nothing if VITE_GOOGLE_CLIENT_ID is not set. */
export default function GoogleSignInButton({ onCredential, onError }) {
  const holder = useRef(null);
  const cb = useRef({ onCredential, onError });
  cb.current = { onCredential, onError };

  useEffect(() => {
    if (!CLIENT_ID) return undefined;
    let cancelled = false;

    loadGsi()
      .then(() => {
        if (cancelled || !holder.current || !window.google?.accounts?.id) return;
        window.google.accounts.id.initialize({
          client_id: CLIENT_ID,
          callback: (resp) => cb.current.onCredential?.(resp.credential),
        });
        window.google.accounts.id.renderButton(holder.current, {
          theme: "outline",
          size: "large",
          text: "signin_with",
          width: 300,
        });
      })
      .catch(() => cb.current.onError?.("Could not load Google sign-in. Check your connection."));

    return () => {
      cancelled = true;
    };
  }, []);

  if (!CLIENT_ID) return null;

  return (
    <div className="mt-4 border-t border-border pt-4">
      <p className="mb-3 text-center font-mono text-[0.65rem] uppercase tracking-wider text-muted-foreground">or</p>
      <div ref={holder} className="flex justify-center" />
    </div>
  );
}
