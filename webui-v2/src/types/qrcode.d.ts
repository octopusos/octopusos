declare module 'qrcode' {
  // Keep typing minimal: QR library is only used to generate a data URL.
  // If consumers need richer typing later, switch to @types/qrcode.
  export function toDataURL(text: string, opts?: any): Promise<string>
  const _default: { toDataURL: typeof toDataURL }
  export default _default
}

