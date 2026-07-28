import React, { useContext } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';
import { Activity, LayoutDashboard, History, FileText, LogOut, User } from 'lucide-react';

const Navbar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useContext(AuthContext);

  const isActive = (path) => {
    return location.pathname === path ? 'text-primary-600 bg-primary-50' : 'text-slate-600 hover:text-primary-600 hover:bg-slate-50';
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link to="/" className="flex items-center space-x-2">
              <Activity className="h-8 w-8 text-primary-600" />
              <span className="text-xl font-bold text-slate-900">AgentCare</span>
            </Link>
          </div>
          
          <div className="hidden sm:flex sm:items-center sm:space-x-4">
            {user ? (
              <>
                <Link to="/dashboard" className={`flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${isActive('/dashboard')}`}>
                  <LayoutDashboard className="h-4 w-4 mr-2" />
                  Dashboard
                </Link>
                <Link to="/history" className={`flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${isActive('/history')}`}>
                  <History className="h-4 w-4 mr-2" />
                  History
                </Link>
                <Link to="/documents" className={`flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${isActive('/documents')}`}>
                  <FileText className="h-4 w-4 mr-2" />
                  Documents
                </Link>
                <div className="ml-4 flex items-center border-l border-slate-200 pl-4 space-x-3">
                  <div className="flex items-center text-sm font-medium text-slate-700">
                    <User className="h-4 w-4 mr-1 text-slate-400" />
                    {user.name}
                  </div>
                  <button 
                    onClick={handleLogout}
                    className="flex items-center px-3 py-2 rounded-md text-sm font-medium text-slate-500 hover:text-red-600 hover:bg-red-50 transition-colors"
                  >
                    <LogOut className="h-4 w-4 mr-1" />
                    Logout
                  </button>
                </div>
              </>
            ) : (
              <div className="flex items-center space-x-4">
                <Link to="/login" className="text-sm font-medium text-slate-600 hover:text-primary-600 transition-colors">
                  Log in
                </Link>
                <Link to="/register" className="text-sm font-medium px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors">
                  Sign up
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
