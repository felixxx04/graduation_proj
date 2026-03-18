import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import ErrorBoundary from './components/ErrorBoundary'
import { PrivacyStoreProvider } from './lib/privacyStore'
import { AuthProvider } from './lib/authStore'
import { PatientStoreProvider } from './lib/patientStore'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <AuthProvider>
        <PatientStoreProvider>
          <PrivacyStoreProvider>
            <App />
          </PrivacyStoreProvider>
        </PatientStoreProvider>
      </AuthProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)
