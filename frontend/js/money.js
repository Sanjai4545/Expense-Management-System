/**
 * Money and percentage parsing and formatting helpers.
 * Note: Floats are disallowed everywhere except inside the single display formatting helper.
 */

const MAX_PAISE = 1_000_000_000; // ₹1 crore

/**
 * Parse a rupee string input into integer paise without floating point math.
 * Returns null if invalid or <= 0 or > MAX_PAISE.
 */
export function parseRupeesToPaise(str) {
  if (typeof str !== "string") return null;
  // 1. Trim. Remove ₹, spaces, and commas.
  const cleaned = str.trim().replace(/₹/g, "").replace(/\s+/g, "").replace(/,/g, "");

  // 2. Must match ^\d{1,9}(\.\d{1,2})?$, otherwise return null
  if (!/^\d{1,9}(\.\d{1,2})?$/.test(cleaned)) {
    return null;
  }

  // 3. Split on ., pad fractional part to 2 digits
  const parts = cleaned.split(".");
  const whole = parseInt(parts[0], 10);
  const fracStr = parts.length > 1 ? parts[1].padEnd(2, "0").slice(0, 2) : "00";
  const frac = parseInt(fracStr, 10);

  const paise = whole * 100 + frac;

  // 4. Return null if result is 0 or exceeds limit
  if (paise === 0 || paise > MAX_PAISE) {
    return null;
  }

  return paise;
}

/**
 * Format paise into Indian Rupee string representation.
 * Single allowed location for float in the frontend.
 */
export function formatPaise(cents) {
  const isNegative = cents < 0;
  const absCents = Math.abs(cents);
  const rupees = absCents / 100;
  const hasDecimals = absCents % 100 !== 0;

  const formatter = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: hasDecimals ? 2 : 0,
    maximumFractionDigits: 2,
  });

  const formatted = formatter.format(rupees);
  return isNegative ? `−${formatted}` : formatted;
}

/**
 * Parse percentage string (up to 2 decimals, e.g. "33.33") to integer basis points (3333).
 * No-float parsing approach. Returns null if invalid.
 */
export function parsePercentToBasisPoints(str) {
  if (typeof str !== "string") return null;
  const cleaned = str.trim().replace(/%/g, "").replace(/\s+/g, "");
  if (!/^\d{1,3}(\.\d{1,2})?$/.test(cleaned)) {
    return null;
  }
  const parts = cleaned.split(".");
  const whole = parseInt(parts[0], 10);
  const fracStr = parts.length > 1 ? parts[1].padEnd(2, "0").slice(0, 2) : "00";
  const frac = parseInt(fracStr, 10);
  const bps = whole * 100 + frac;
  if (bps < 0 || bps > 10000) {
    return null;
  }
  return bps;
}

/**
 * Format basis points (e.g. 3333 -> "33.33%") without floats.
 */
export function formatBasisPoints(bps) {
  const whole = Math.floor(bps / 100);
  const frac = bps % 100;
  if (frac === 0) {
    return `${whole}%`;
  }
  return `${whole}.${String(frac).padStart(2, "0")}%`;
}
