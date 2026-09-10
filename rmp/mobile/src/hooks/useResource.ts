import { useCallback, useEffect, useRef, useState } from "react";
// Load on mount or an explicit selection change. No polling or focus reloads.
export function useResource<T>(fetcher: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const request = useRef(0);
  const reload = useCallback(async () => {
    const version = ++request.current;
    setBusy(true);
    setError("");
    try {
      const result = await fetcher();
      if (version === request.current) setData(result);
    } catch (e) {
      if (version === request.current)
        setError(
          e instanceof Error
            ? e.message
            : "Unable to load. Pull down to try again.",
        );
    } finally {
      if (version === request.current) setBusy(false);
    }
  }, [fetcher]);
  useEffect(() => {
    setData(null);
    void reload();
    return () => {
      ++request.current;
    };
  }, [reload]);
  return { data, setData, error, busy, reload };
}
