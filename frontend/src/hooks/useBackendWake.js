import { useEffect, useState } from "react";
import { fetchHealth } from "../api/client";

export function useBackendWake() {
  const [isWaking, setIsWaking] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      while (!cancelled) {
        try {
          const res = await fetchHealth();
          if (res.ok) {
            if (!cancelled) setIsWaking(false);
            return;
          }
        } catch {
        }
        await new Promise((r) => setTimeout(r, 3000));
      }
    }

    poll();
    return () => { cancelled = true; };
  }, []);

  return { isWaking };
}
