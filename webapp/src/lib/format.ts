// Small pure formatting helpers. No contract / network access here.

export function shortAddr(a: string | undefined | null, size = 4): string {
  if (!a) return "—";
  if (a.length <= 2 + size * 2) return a;
  return `${a.slice(0, 2 + size)}…${a.slice(-size)}`;
}

export function sameAddr(a?: string | null, b?: string | null): boolean {
  if (!a || !b) return false;
  return a.toLowerCase() === b.toLowerCase();
}

// bytes fields decode as "0x" (empty) or "0x<hex>".
export function isEmptyHex(h: string | undefined | null): boolean {
  return !h || h === "0x" || h === "0x0" || h === "";
}

export function shortHex(h: string | undefined | null, size = 6): string {
  if (isEmptyHex(h)) return "—";
  const s = h as string;
  if (s.length <= 2 + size * 2) return s;
  return `${s.slice(0, 2 + size)}…${s.slice(-size)}`;
}

const WEI_PER_GEN = 1_000_000_000_000_000_000n;

// Format a wei bigint as a GEN string with up to `maxFrac` decimals,
// trailing zeros trimmed.
export function formatGen(wei: bigint | number | string, maxFrac = 6): string {
  const v = typeof wei === "bigint" ? wei : BigInt(wei ?? 0);
  const neg = v < 0n;
  const abs = neg ? -v : v;
  const whole = abs / WEI_PER_GEN;
  const frac = abs % WEI_PER_GEN;
  let fracStr = frac.toString().padStart(18, "0").slice(0, maxFrac);
  fracStr = fracStr.replace(/0+$/, "");
  const body = fracStr ? `${whole}.${fracStr}` : `${whole}`;
  return `${neg ? "-" : ""}${body} GEN`;
}

export function bigintReplacer(_k: string, v: unknown): unknown {
  return typeof v === "bigint" ? v.toString() : v;
}

export function prettyJson(value: unknown): string {
  return JSON.stringify(value, bigintReplacer, 2);
}

// Turn a raw contract error into a short readable line. genlayer-js wraps
// gl.vm.UserError messages in various ways; pull the human bit out.
export function readableError(e: unknown): string {
  if (!e) return "Unknown error";
  const raw =
    typeof e === "string"
      ? e
      : e instanceof Error
        ? e.message
        : (() => {
            try {
              return JSON.stringify(e, bigintReplacer);
            } catch {
              return String(e);
            }
          })();
  // Common GenLayer patterns.
  const m =
    raw.match(/UserError\(["']?(.+?)["']?\)/)?.[1] ??
    raw.match(/reverted?:?\s*(.+)/i)?.[1] ??
    raw.match(/"message"\s*:\s*"([^"]+)"/)?.[1];
  return (m ?? raw).slice(0, 400);
}

export function isUndeterminedError(e: unknown): boolean {
  const s = (readableError(e) + " " + String(e)).toLowerCase();
  return (
    s.includes("undetermined") ||
    s.includes("majority_disagree") ||
    s.includes("majority disagree") ||
    s.includes("adjudication output rejected") ||
    s.includes("consensus") && s.includes("disagree")
  );
}
