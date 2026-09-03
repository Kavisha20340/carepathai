import React from 'react';
import { FaExclamationTriangle, FaPhoneAlt, FaRedo } from 'react-icons/fa';
import { useStore } from '../store/useStore';
import { translations } from '../utils/translations';
import { useNavigate } from 'react-router-dom';

export default function EmergencyOverlay() {
  const { emergencyMessage, resetSession, language } = useStore();
  const navigate = useNavigate();

  if (!emergencyMessage) return null;

  const t = translations[language || 'en'];

  // Smart translation override: if the session language is Hindi, display the translated alert text
  const displayedMessage = language === 'hi' ? t.emergencyAlertText : (emergencyMessage || t.emergencyAlertText);

  const handleRestart = () => {
    resetSession(true); // Clear language preference & return to landing page
    navigate('/');
  };

  return (
    <div className="fixed inset-0 bg-red-600/95 dark:bg-red-950/95 backdrop-blur-md z-50 flex items-center justify-center p-4 animate-fadeIn">
      <div className="bg-white dark:bg-gray-900 rounded-3xl max-w-lg w-full p-8 shadow-2xl border-4 border-red-500 text-center animate-scaleIn">
        <div className="w-20 h-20 bg-red-100 dark:bg-red-900/30 text-red-600 rounded-full flex items-center justify-center mx-auto mb-6 shadow-inner">
          <FaExclamationTriangle className="text-4xl animate-bounce" />
        </div>

        <h1 className="text-2xl md:text-3xl font-extrabold text-red-600 dark:text-red-500 mb-4 tracking-tight">
          {t.criticalAlert}
        </h1>

        <div className="p-4 bg-red-50 dark:bg-red-950/25 border border-red-100 dark:border-red-900/40 rounded-2xl mb-6">
          <p className="text-base text-gray-850 dark:text-gray-200 font-bold leading-relaxed">
            {displayedMessage}
          </p>
        </div>

        <p className="text-sm text-gray-500 dark:text-gray-400 mb-8 font-medium">
          {t.emergencySuspendedText}
        </p>

        <div className="flex flex-col gap-3">
          <a
            href="tel:112"
            className="w-full py-4 bg-red-600 hover:bg-red-700 text-white rounded-2xl font-extrabold flex items-center justify-center gap-3 transition-colors shadow-lg shadow-red-100 dark:shadow-none"
          >
            <FaPhoneAlt />
            <span>{t.btnCall112}</span>
          </a>

          <button
            onClick={handleRestart}
            className="w-full py-3.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-2xl font-extrabold flex items-center justify-center gap-2 transition-colors border border-gray-200 dark:border-gray-700 cursor-pointer"
          >
            <FaRedo className="text-xs" />
            <span>{t.btnRestart}</span>
          </button>
        </div>
      </div>
    </div>
  );
}