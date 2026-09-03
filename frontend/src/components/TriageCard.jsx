import React from 'react';
import { FaHeartbeat, FaInfoCircle, FaUserMd } from 'react-icons/fa';
import { useStore } from '../store/useStore';
import { translations, specialistTranslations } from '../utils/translations';

export default function TriageCard() {
  const { triageResult, sessionState, language } = useStore();

  if (!triageResult) return null;

  const { urgency_level, specialist_type, confidence, reasoning_summary } = triageResult;

  const t = translations[language || 'en'];
  const sT = specialistTranslations[language || 'en'];

  const urgencyColors = {
    self_care: 'bg-green-100 dark:bg-green-950/40 text-green-800 dark:text-green-400 border-green-200 dark:border-green-900/50',
    routine: 'bg-blue-100 dark:bg-blue-950/40 text-blue-800 dark:text-blue-400 border-blue-200 dark:border-blue-900/50',
    urgent: 'bg-orange-100 dark:bg-orange-950/40 text-orange-800 dark:text-orange-400 border-orange-200 dark:border-orange-900/50',
    emergency: 'bg-red-100 dark:bg-red-950/40 text-red-800 dark:text-red-400 border-red-200 dark:border-red-900/50'
  };

  const urgencyLabels = {
    self_care: t.self_care,
    routine: t.routine,
    urgent: t.urgent,
    emergency: t.emergency
  };

  const confidenceLabels = {
    high: t.high,
    moderate: t.moderate,
    low: t.low
  };

  const slotLabels = {
    chief_complaint: t.chiefComplaint,
    body_location: t.bodyLocation,
    onset: t.onset,
    duration: t.duration,
    severity: t.severity,
    associated_symptoms: t.associatedSymptoms,
    aggravating_factors: t.aggravatingFactors
  };

  return (
    <div className="w-full max-w-2xl mx-auto flex flex-col gap-6 p-6 bg-white dark:bg-gray-800 rounded-3xl shadow-xl border border-gray-100 dark:border-gray-700 animate-fadeIn">
      
      {/* Triage Summary Header */}
      <div className="flex items-center gap-3 pb-4 border-b border-gray-100 dark:border-gray-700">
        <FaHeartbeat className="text-3xl text-indigo-600 animate-pulse" />
        <div className="text-left">
          <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100">{t.cardTitle}</h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">Deterministic slot-filling diagnosis fallback applied</p>
        </div>
      </div>

      {/* Main Badges */}
      <div className="grid grid-cols-2 gap-4">
        <div className={`p-4 rounded-2xl border text-center ${urgencyColors[urgency_level] || urgencyColors.routine}`}>
          <span className="block text-xs uppercase tracking-wider font-semibold opacity-75">{t.urgencyLevel}</span>
          <span className="text-lg font-bold">{urgencyLabels[urgency_level] || urgency_level}</span>
        </div>

        <div className="p-4 rounded-2xl border border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 text-center">
          <span className="block text-xs uppercase tracking-wider font-semibold text-gray-400 dark:text-gray-500">{t.specialistType}</span>
          <div className="flex items-center justify-center gap-1.5 mt-1.5 text-gray-800 dark:text-gray-200 font-bold">
            <FaUserMd className="text-indigo-500 text-sm" />
            <span>{sT[specialist_type] || specialist_type}</span>
          </div>
        </div>
      </div>

      {/* Reasoning Summary */}
      <div className="p-4 rounded-2xl bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-100/30 text-left">
        <div className="flex items-center gap-2 mb-1.5 text-indigo-800 dark:text-indigo-400 font-semibold text-sm">
          <FaInfoCircle />
          <span>{t.clinicalReasoning}</span>
        </div>
        <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed font-medium">
          {reasoning_summary}
        </p>
        <span className="inline-block mt-2 text-[10px] text-gray-400 dark:text-gray-500 bg-white dark:bg-gray-900 px-2.5 py-0.5 rounded-full border border-gray-100 dark:border-800 font-bold">
          {t.confidence}: {confidenceLabels[confidence] || confidence}
        </span>
      </div>

      {/* Extracted Slots (Transparency Layer) */}
      <div className="border-t border-gray-100 dark:border-gray-700 pt-4">
        <h3 className="text-sm font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider text-left mb-3">{t.extractedSlotMetadata}</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
          {Object.entries(sessionState).map(([key, val]) => {
            if (key === 'red_flags_present' || key === 'relevant_history') return null;
            const isFilled = val !== null && val !== undefined && (!Array.isArray(val) || val.length > 0);
            
            // Format duration values nice and short if they are localized Hindi arrays
            let displayVal = 'Not Captured';
            if (isFilled) {
              if (Array.isArray(val)) {
                displayVal = val.join(', ');
              } else {
                displayVal = val.toString();
              }
            }

            return (
              <div key={key} className="flex justify-between items-center p-2.5 bg-gray-50/50 dark:bg-gray-900/50 rounded-xl border border-gray-100/40 dark:border-gray-800/40 text-xs">
                <span className="font-semibold text-gray-500 dark:text-gray-400">{slotLabels[key] || key}</span>
                <span className={`font-bold capitalize truncate max-w-[160px] ${isFilled ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-300 dark:text-gray-600'}`}>
                  {isFilled ? displayVal : t.notCaptured}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}