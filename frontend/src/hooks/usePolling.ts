import { useEffect, useRef, useCallback } from "react";

export function usePolling(
  fn: () => Promise<void>,
  intervalMs: number,
  active: boolean
): void {
  const savedFn = useRef(fn);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    savedFn.current = fn;
  }, [fn]);

  const stop = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!active) {
      stop();
      return;
    }

    // Immediate first call
    savedFn.current();

    timerRef.current = setInterval(() => {
      savedFn.current();
    }, intervalMs);

    return stop;
  }, [active, intervalMs, stop]);
}
