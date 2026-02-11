import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'
import './i18n' // Initialize i18n
import { initializeRuntimeConfig, assertRuntimeOriginConsistency } from '@/platform/config/runtimeConfig'

async function bootstrap() {
  await initializeRuntimeConfig()
  assertRuntimeOriginConsistency()

  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <App />
      </BrowserRouter>
    </React.StrictMode>,
  )
}

void bootstrap()
