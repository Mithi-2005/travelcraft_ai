export const APP_CURRENCY_CODE = "INR";
export const SUPPORTED_CURRENCIES = [APP_CURRENCY_CODE];

export function formatCurrency(value, currencyCode = APP_CURRENCY_CODE) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return `${APP_CURRENCY_CODE} ${value ?? ""}`.trim();
  }

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: currencyCode || APP_CURRENCY_CODE,
    maximumFractionDigits: numericValue >= 100 ? 0 : 2,
  }).format(numericValue);
}
