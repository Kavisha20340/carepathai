import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { FaSync } from 'react-icons/fa';
import { useStore } from './store/useStore';
import LandingPage from './components/LandingPage';
import MicInput from './components/MicInput';
import ConversationDisplay from './components/ConversationDisplay';
import TriageCard from './components/TriageCard';
import DoctorSearch from './components/DoctorSearch';
import EmergencyOverlay from './components/EmergencyOverlay';
import ErrorBoundary from './components/ErrorBoundary';
import { translations } from './utils/translations';

function AppContent() {
  const { triageResult, sessionId, resetSession, turnCount, maxTurns, language, setLanguage } = useStore();
  const navigate = useNavigate();
  const location = useLocation();

  const isLandingPath = location.pathname === '/';
  const t = translations[isLandingPath ? 'en' : (language || 'en')];

  useEffect(() => {
    if (location.pathname === '/triage' && !language) {
      navigate('/', { replace: true });
    }
  }, [language, location.pathname, navigate]);

  const handleResetDemo = () => {
    resetSession(true);
    navigate('/');
  };

  const isTriagePath = location.pathname === '/triage';

  const isResultsView = triageResult && location.pathname === '/triage';

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-800 dark:text-gray-100 flex flex-col font-sans transition-colors duration-200">
      <EmergencyOverlay />

      <header className="sticky top-0 z-30 w-full bg-white/80 dark:bg-gray-900/80 backdrop-blur-md py-2 border-b border-gray-100 dark:border-gray-800/40">
        <div className="mx-auto w-full max-w-2xl px-6 md:px-10 flex items-center justify-between transition-all duration-300">
          <div className="w-full mx-auto max-w-xl flex items-center justify-between">
            <div className="text-left flex flex-col justify-center">
              <h1 className="text-xs md:text-sm font-bold tracking-tight text-gray-950 dark:text-white m-0 leading-none">
                {t.logo}
              </h1>
              <p className={`font-semibold text-indigo-600 dark:text-indigo-400 m-0 mt-0.5 leading-none ${
                t === translations.en ? 'text-[12px] md:text-[14px]' : 'text-[10px] md:text-xs'
              }`}>
                {t.subtitle}
              </p>
            </div>

            <div className="flex items-center gap-3">
              {isTriagePath && language && (
                <div className="flex items-center bg-gray-100 dark:bg-gray-855 rounded-xl p-1 border border-gray-200 dark:border-gray-800 shadow-inner">
                  <button
                    onClick={() => setLanguage('en')}
                    className={`px-3 py-1 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                      language === 'en'
                        ? 'bg-white dark:bg-gray-700 text-indigo-600 dark:text-indigo-400 shadow-sm'
                        : 'text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                    }`}
                  >
                    EN
                  </button>
                  <button
                    onClick={() => setLanguage('hi')}
                    className={`px-3 py-1 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                      language === 'hi'
                        ? 'bg-white dark:bg-gray-700 text-emerald-600 dark:text-emerald-400 shadow-sm'
                        : 'text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                    }`}
                  >
                    हिंदी
                  </button>
                </div>
              )}

              {isTriagePath && (
                <button
                  onClick={handleResetDemo}
                  className="px-4 py-2 bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/40 dark:hover:bg-indigo-900/40 text-indigo-700 dark:text-indigo-400 rounded-xl font-bold flex items-center gap-2 text-xs transition-all cursor-pointer"
                  title="New Chat"
                >
                  <FaSync className="text-[10px]" />
                  <span>{t.resetBtn}</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className={`flex-grow flex flex-col items-center justify-center pt-4 ${isLandingPath ? 'pb-6' : 'pb-16'} px-6 md:px-10 w-full mx-auto gap-6 transition-all duration-300 ${isResultsView ? 'max-w-5xl' : 'max-w-2xl'}`}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/triage" element={
            !triageResult ? (
              <div className="w-full max-w-2xl mx-auto flex flex-col bg-white dark:bg-gray-800 rounded-2xl shadow-md border border-gray-100 dark:border-gray-800 overflow-hidden animate-fadeIn">
                <ConversationDisplay />
                <MicInput />
              </div>
            ) : (
              <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-6 animate-slideIn items-start">
                <TriageCard />
                <DoctorSearch />
              </div>
            )
          } />
        </Routes>
      </main>

      <footer className="py-3 bg-white/50 dark:bg-gray-950/20 text-center text-xs text-gray-400 font-medium">
        <div className="mx-auto w-full max-w-2xl px-6 md:px-10 transition-all duration-300">
          <div className="w-full mx-auto border-t border-gray-150 dark:border-gray-850 pt-3 max-w-xl">
            <p>{t.footerText.replace('{year}', new Date().getFullYear())}</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <Router>
        <AppContent />
      </Router>
    </ErrorBoundary>
  );
}
