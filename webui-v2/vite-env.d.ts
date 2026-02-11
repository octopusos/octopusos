/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_PUBLIC_ORIGIN: string
  readonly VITE_API_TIMEOUT: string
  readonly VITE_ENABLE_DEMO_MODE: string
  readonly VITE_ENABLE_MOCK: string
  readonly DEV: boolean
  readonly PROD: boolean
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare const __APP_PRODUCT_NAME__: string
declare const __APP_WEBUI_NAME__: string
declare const __APP_RELEASE_VERSION__: string
declare const __APP_BUILD_VERSION__: string
