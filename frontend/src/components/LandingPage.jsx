import React from 'react';
import { FaHeartbeat, FaComments, FaGlobe } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import { useStore } from '../store/useStore';
import { translations } from '../utils/translations';

export default function LandingPage() {
  const navigate = useNavigate();
  const { setLanguage } = useStore();

  const handleSelectLanguage = (lang) => {
    setLanguage(lang);
    navigate('/triage');
  };

  const tEN = translations.en;
  const tHI = translations.hi;

  return (
    <div className="w-full max-w-xl mx-auto py-1 animate-fadeIn flex items-center justify-center">
      <div className="w-full bg-white dark:bg-gray-800 p-5 md:p-6 rounded-xl shadow-md text-center">
        
        {/* Brand Icon */}
        <div className="w-11 h-11 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 rounded-xl flex items-center justify-center mx-auto mb-3 shadow-inner animate-pulse">
          <FaHeartbeat className="text-2xl" />
        </div>

        {/* Dynamic Multi-lingual Titles */}
        <div className="space-y-0.5 mb-4">
          <h2 className="text-lg md:text-xl font-extrabold text-gray-950 dark:text-white tracking-tight">
            {tEN.landingTitle}
          </h2>
          <h3 className="text-sm md:text-base font-bold text-indigo-600 dark:text-indigo-400">
            {tHI.landingTitle}
          </h3>
        </div>

        {/* Dual Language Descriptions */}
        <div className="space-y-1.5 max-w-md mx-auto mb-6 text-[11px] text-gray-500 dark:text-gray-400 font-medium leading-relaxed">
          <p>{tEN.landingSubtitle}</p>
          <div className="w-10 h-[1px] bg-gray-150 dark:bg-gray-700 mx-auto my-0.5"></div>
          <p className="text-gray-600 dark:text-gray-300">{tHI.landingSubtitle}</p>
        </div>

        {/* Symmetric Card Selection Buttons */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-md mx-auto w-full">
          
          {/* English Selector Card */}
          <button
            onClick={() => handleSelectLanguage('en')}
            className="flex flex-col items-center text-center p-4 border border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-900/50 hover:bg-white dark:hover:bg-gray-850 hover:border-indigo-500 dark:hover:border-indigo-400 rounded-xl transition-all shadow-sm hover:shadow active:scale-[0.98] cursor-pointer h-full justify-between gap-2"
          >
            <div className="p-2 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 rounded-lg">
              <FaGlobe className="text-base" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-gray-900 dark:text-white mb-0.5">
                {tEN.landingEngButton}
              </h4>
              <p className="text-[10px] text-gray-400 dark:text-gray-500 leading-relaxed max-w-[150px] mx-auto">
                Assess symptoms and find specialists in English.
              </p>
            </div>
          </button>

          {/* Hindi Selector Card */}
          <button
            onClick={() => handleSelectLanguage('hi')}
            className="flex flex-col items-center text-center p-4 border border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-900/50 hover:bg-white dark:hover:bg-gray-850 hover:border-emerald-500 dark:hover:border-emerald-400 rounded-xl transition-all shadow-sm hover:shadow active:scale-[0.98] cursor-pointer h-full justify-between gap-2"
          >
            <div className="p-2 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 rounded-lg">
              <FaComments className="text-base" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-gray-900 dark:text-white mb-0.5">
                {tHI.landingHindiButton}
              </h4>
              <p className="text-[10px] text-gray-400 dark:text-gray-500 leading-relaxed max-w-[150px] mx-auto">
                अपनी पसंदीदा भाषा हिंदी में लक्षणों का आकलन करें और डॉक्टर खोजें।
              </p>
            </div>
          </button>

        </div>

      </div>
    </div>
  );
}