import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import PatientRecords from './pages/PatientRecords'
import PrivacyConfig from './pages/PrivacyConfig'
import DrugRecommendation from './pages/DrugRecommendation'
import LoginPage from './pages/LoginPage'
import ForbiddenPage from './pages/ForbiddenPage'
import AdminDashboard from './pages/AdminDashboard'
import MyRecords from './pages/MyRecords'
import ReviewDashboard from './pages/ReviewDashboard'
import DrugDatabase from './pages/DrugDatabase'
import RecommendationStats from './pages/RecommendationStats'
import { RequireRole } from './components/AuthGuards'

function App() {
  return (
    <Router>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forbidden" element={<ForbiddenPage />} />

        {/* App shell is public */}
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />

          {/* Patient only */}
          <Route element={<RequireRole role="patient" />}>
            <Route path="recommendation/*" element={<DrugRecommendation />} />
            <Route path="my-records/*" element={<MyRecords />} />
          </Route>

          {/* Doctor + Admin */}
          <Route element={<RequireRole roles={['doctor', 'admin']} />}>
            <Route path="patients/*" element={<PatientRecords />} />
            <Route path="review/*" element={<ReviewDashboard />} />
          </Route>

          {/* Admin only */}
          <Route element={<RequireRole role="admin" />}>
            <Route path="drug-database/*" element={<DrugDatabase />} />
            <Route path="recommendation-stats/*" element={<RecommendationStats />} />
            <Route path="privacy/*" element={<PrivacyConfig />} />
            <Route path="admin/*" element={<AdminDashboard />} />
          </Route>
        </Route>
      </Routes>
    </Router>
  )
}

export default App
