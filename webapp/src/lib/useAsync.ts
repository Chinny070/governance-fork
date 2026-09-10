import { useCallback, useEffect, useRef, useState } from "react";
import { readableError } from "./format";

export interface AsyncState<T> {
  data: T | undefined;
  loading: boolean;
  error: string | null;
  refresh: () => void;
  /** Increments on every completed refresh — handy as an effect dep. */
  version: number;
}

/**
 * Runs `fn` on mount and whenever a dependency in `deps` changes, plus on
 * an explicit refresh(). Ignores stale resolutions.
 */
export function useAsync<T>(
  fn: () => Promise<T>,
  deps: unknown[] = [],
): AsyncState<T> {
  const [data, setData] = useState<T | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const [nonce, setNonce] = useState(0);
  const runId = useRef(0);

  const refresh = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    const id = ++runId.current;
    setLoading(true);
    setError(null);
    fn()
      .then((res) => {
        if (id !== runId.current) return;
        setData(res);
        setVersion((v) => v + 1);
      })
      .catch((e) => {
        if (id !== runId.current) return;
        setError(readableError(e));
      })
      .finally(() => {
        if (id === runId.current) setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  return { data, loading, error, refresh, version };
}
