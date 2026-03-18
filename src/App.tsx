import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import PatientRecords from './pages/PatientRecords'
import PrivacyConfig from './pages/PrivacyConfig'
import DrugRecommendation from './pages/DrugRecommendation'
import PrivacyVisualization from './pages/PrivacyVisualization'
import LoginPage from './pages/LoginPage'
import ForbiddenPage from './pages/ForbiddenPage'
import AdminDashboard from './pages/AdminDashboard'
import { RequireAuthModal, RequireRole } from './components/AuthGuards'

function App() {
  return (
    <Router>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forbidden" element={<ForbiddenPage />} />

        {/* App shell is public; feature pages are protected via modal */}
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />

          <Route element={<RequireAuthModal />}>
            <Route path="recommendation/*" element={<DrugRecommendation />} />
            <Route path="visualization/*" element={<PrivacyVisualization />} />
          </Route>

          <Route element={<RequireRole role="admin" />}>
            <Route path="patients/*" element={<PatientRecords />} />
            <Route path="privacy/*" element={<PrivacyConfig />} />
          </Route>

          <Route element={<RequireRole role="admin" />}>
            <Route path="admin/*" element={<AdminDashboard />} />
          </Route>
        </Route>
      </Routes>
    </Router>
  )
}

export default App
