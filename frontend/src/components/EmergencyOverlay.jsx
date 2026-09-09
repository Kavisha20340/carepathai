import React, { useEffect } from 'react';
import { FaExclamationTriangle, FaPhoneAlt, FaRedo, FaBriefcaseMedical, FaBaby, FaBrain, FaRegCommentDots, FaSkull } from 'react-icons/fa';
import { useStore } from '../store/useStore';
import { translations } from '../utils/translations';
import { getEmergencyNumbers } from '../utils/emergencyData';
import { useNavigate } from 'react-router-dom';

const getIcon = (type) => {
  if (type === 'medical') return <FaBriefcaseMedical className="text-orange-500" />;
  if (type === 'baby') return <FaBaby className="text-pink-500" />;
  if (type === 'brain') return <FaBrain className="text-purple-500" />;
  if (type === 'chat') return <FaRegCommentDots className="text-teal-500" />;
  if (type === 'poison') return <FaSkull className="text-gray-600" />;
  return <FaPhoneAlt className="text-red-600" />;
};

export default function EmergencyOverlay() {
  const { emergencyMessage, resetSession, language, isLoading } = useStore();
  const navigate = useNavigate();

  // Lock body scroll while emergency overlay is displayed to eliminate double scrollbars
  useEffect(() => {
    if (emergencyMessage) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [emergencyMessage]);

  if (!emergencyMessage) return null;

  const t = translations[language || 'en'];
  const displayedMessage = emergencyMessage || t.emergencyAlertText;

  const handleRestart = () => {
    resetSession(true);
    navigate('/');
  };

  const list = getEmergencyNumbers()[language || 'en'] || [];
  const primaryNumbers = list.filter(n => n.primary);
  const secondaryNumbers = list.filter(n => !n.primary);

  return (
    <div className="fixed inset-0 z-40 flex justify-center pt-32 sm:pt-36 pb-8 overflow-y-auto [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden pointer-events-none animate-fadeIn">
      <div className="w-full max-w-2xl px-4 sm:px-6 md:px-10 pointer-events-auto">
        <div className="bg-red-600/90 dark:bg-red-950/90 backdrop-blur-md rounded-3xl p-3 sm:p-5 shadow-2xl border-2 border-red-500/80 text-center animate-scaleIn">
          <div className="bg-white dark:bg-gray-900 rounded-2xl px-3.5 sm:px-7 md:px-8 pb-3.5 sm:pb-4 md:pb-5 pt-5 shadow-inner border border-red-200 dark:border-red-900/50">
            {/* Title Header */}
            <div className="flex flex-col items-center justify-center mb-2">
              <h1 className="text-xs sm:text-sm font-black text-red-600 dark:text-red-500 tracking-wide uppercase whitespace-nowrap leading-none px-3 py-1.5 bg-red-50 dark:bg-red-950/20 rounded-lg inline-block">
                {t.criticalAlert}
              </h1>
            </div>

            {/* Emergency Alert Message (with Sparkling Translation Shimmer) */}
            <div className="p-3 bg-red-50 dark:bg-red-950/25 border border-red-100 dark:border-red-900/40 rounded-xl mb-3 text-left">
              {isLoading ? (
                <div className="space-y-2 py-1 animate-pulse">
                  <div className="h-3.5 bg-red-200/60 dark:bg-red-900/50 rounded w-full"></div>
                  <div className="h-3.5 bg-red-200/60 dark:bg-red-900/50 rounded w-4/5 mx-auto"></div>
                </div>
              ) : (
                <p className="text-xs md:text-sm text-gray-850 dark:text-gray-200 font-bold leading-relaxed text-center">
                  {displayedMessage}
                </p>
              )}
            </div>

            {/* Primary CTAs (112 & 108) */}
            <div className="grid grid-cols-2 gap-2 mb-3">
              {primaryNumbers.map((p, idx) => (
                <a
                  key={idx}
                  href={`tel:${p.number}`}
                  className="py-2.5 px-3 bg-red-600 hover:bg-red-700 text-white rounded-xl font-extrabold flex items-center justify-center gap-2 transition-colors shadow-sm text-center group cursor-pointer"
                >
                  <FaPhoneAlt className="text-sm md:text-base flex-shrink-0" />
                  <span className="text-xs md:text-sm tracking-wide font-black">{p.number} — {p.title.split(' — ')[1] || p.title}</span>
                </a>
              ))}
            </div>

            {/* Secondary Specialized Helpline List */}
            <div className="flex flex-col gap-1.5 mb-3 text-left">
              {secondaryNumbers.map((s, idx) => (
                <div key={idx} className="flex items-center justify-between gap-2 p-1.5 px-2.5 bg-gray-50 dark:bg-gray-800/60 rounded-xl border border-gray-150 dark:border-gray-750">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="p-1.5 bg-white dark:bg-gray-700 rounded-lg text-xs flex-shrink-0">
                      {getIcon(s.iconType)}
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-[11px] font-bold text-gray-850 dark:text-gray-150 truncate leading-tight">
                        {s.title}
                      </h3>
                      <p className="text-[9px] text-gray-500 dark:text-gray-400 truncate leading-tight">
                        {s.desc}
                      </p>
                    </div>
                  </div>
                  <a
                    href={`tel:${s.number}`}
                    className="w-28 h-7 px-2 bg-white hover:bg-gray-100 dark:bg-gray-700 dark:hover:bg-gray-650 text-gray-850 dark:text-gray-150 text-[10px] font-extrabold rounded-lg flex items-center justify-center gap-1 transition-all border border-gray-200 dark:border-gray-600 flex-shrink-0 whitespace-nowrap cursor-pointer"
                  >
                    <FaPhoneAlt className="text-[8px] text-red-600 flex-shrink-0" />
                    <span className="whitespace-nowrap">{s.displayNumber || s.number}</span>
                  </a>
                </div>
              ))}
            </div>

            {/* Standalone Full-Width Start Over Button at Bottom */}
            <button
              onClick={handleRestart}
              className="w-full py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-xl font-extrabold text-xs flex items-center justify-center gap-2 transition-colors border border-gray-200 dark:border-gray-700 cursor-pointer"
            >
              <FaRedo className="text-[10px]" />
              <span>{t.btnRestart}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}