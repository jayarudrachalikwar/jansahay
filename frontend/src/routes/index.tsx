import { BrowserRouter, Route, Routes } from "react-router-dom";
import AdminProtectedRoute from "../components/auth/AdminProtectedRoute";
import FarmerProtectedRoute from "../components/auth/FarmerProtectedRoute";
import ProtectedRoute from "../components/auth/ProtectedRoute";
import MainLayout from "../layouts/MainLayout";
import AdminDocumentsPage from "../pages/admin/AdminDocumentsPage";
import AdminFarmersPage from "../pages/admin/AdminFarmersPage";
import AdminSchemeFormPage from "../pages/admin/AdminSchemeFormPage";
import AdminSchemesPage from "../pages/admin/AdminSchemesPage";
import DashboardPage from "../pages/auth/DashboardPage";
import LoginPage from "../pages/auth/LoginPage";
import RegisterPage from "../pages/auth/RegisterPage";
import FarmerProfilePage from "../pages/profile/FarmerProfilePage";
import HomePage from "../pages/public/HomePage";
import AssistantPage from "../pages/assistant/AssistantPage";
import FarmerRecommendationsPage from "../pages/farmer/FarmerRecommendationsPage";
import FarmerSavedSchemesPage from "../pages/farmer/FarmerSavedSchemesPage";
import FarmerSettingsPage from "../pages/farmer/FarmerSettingsPage";
import FarmerApplicationsPage from "../pages/farmer/FarmerApplicationsPage";
import FarmerApplicationPage from "../pages/farmer/FarmerApplicationPage";
import SchemeDetailsPage from "../pages/schemes/SchemeDetailsPage";
import SchemesPage from "../pages/schemes/SchemesPage";

export default function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<DashboardPage />} />
          </Route>

          <Route element={<FarmerProtectedRoute />}>
            <Route path="/profile" element={<FarmerProfilePage />} />
            <Route path="/schemes" element={<SchemesPage />} />
            <Route path="/schemes/:id" element={<SchemeDetailsPage />} />
            <Route path="/assistant" element={<AssistantPage />} />
            <Route path="/farmer/recommendations" element={<FarmerRecommendationsPage />} />
            <Route path="/farmer/saved" element={<FarmerSavedSchemesPage />} />
            <Route path="/farmer/applications" element={<FarmerApplicationsPage />} />
            <Route path="/farmer/applications/:schemeId" element={<FarmerApplicationPage />} />
            <Route path="/farmer/settings" element={<FarmerSettingsPage />} />
          </Route>

          <Route element={<AdminProtectedRoute />}>
            <Route path="/admin/documents" element={<AdminDocumentsPage />} />
            <Route path="/admin/schemes" element={<AdminSchemesPage />} />
            <Route path="/admin/schemes/new" element={<AdminSchemeFormPage />} />
            <Route path="/admin/schemes/:id/edit" element={<AdminSchemeFormPage />} />
            <Route path="/admin/farmers" element={<AdminFarmersPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
