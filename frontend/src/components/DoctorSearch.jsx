import React, { useState, useEffect } from 'react';
import { FaMapMarkerAlt, FaSearch, FaStar, FaPhoneAlt, FaDirections } from 'react-icons/fa';
import { useStore } from '../store/useStore';
import { translations, specialistTranslations } from '../utils/translations';

export default function DoctorSearch() {
  const { triageResult, doctors, searchDoctors, isLoading, setError, language } = useStore();
  const [radiusInput, setRadiusInput] = useState("10");
  const [isCustomRadius, setIsCustomRadius] = useState(false);
  const [coords, setCoords] = useState(null);
  const [locState, setLocState] = useState('idle');

  const t = translations[language || 'en'];
  const sT = specialistTranslations[language || 'en'];

  useEffect(() => {
    if (triageResult && !coords) {
      setLocState('fetching');
      navigator.geolocation.getCurrentPosition(
        (p) => {
          setCoords({ lat: p.coords.latitude, lng: p.coords.longitude });
          setLocState('success');
        },
        (err) => {
          console.error(err);
          setCoords({ lat: 12.9716, lng: 77.5946 }); // Default Bangalore
          setLocState('success');
          setError("Location permission denied. Used Bangalore defaults for demo.");
        }
      );
    }
  }, [triageResult]);

  const handleSearch = async () => {
    if (!coords || !triageResult) return;
    
    // Extract numerical value and decimal points, e.g. "30km" -> "30", "3.5km" -> "3.5"
    const cleanRadius = radiusInput.replace(/[^0-9.]/g, '');
    const parsedRadius = parseFloat(cleanRadius);
    const finalRadius = isNaN(parsedRadius) || parsedRadius <= 0 ? 10.0 : parsedRadius;
    
    await searchDoctors(triageResult.specialist_type, coords.lat, coords.lng, finalRadius);
  };

  if (!triageResult) return null;

  const specialist_type = triageResult.specialist_type;
  const translatedSpecialist = sT[specialist_type] || specialist_type;

  return (
    <div className="w-full max-w-2xl mx-auto flex flex-col gap-6 p-6 bg-white dark:bg-gray-800 rounded-3xl shadow-xl">
      {/* Search Specialists Header */}
      <div className="flex items-center gap-3 pb-4 border-b border-gray-150 dark:border-gray-700">
        <FaMapMarkerAlt className="text-3xl text-indigo-600 animate-pulse flex-shrink-0" />
        <div className="text-left">
          <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100">{t.stepSearchNearby}</h2>
        </div>
      </div>

      {/* Radius Controls Bar */}
      <div className="flex items-center justify-between p-3.5 bg-gray-50/50 dark:bg-gray-900/50 rounded-2xl border border-gray-100/40 dark:border-gray-800/40 text-xs">
        <div className="flex flex-col gap-0.5 text-left">
          <span className="font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">{t.radiusLabel}</span>
          {locState === 'fetching' && (
            <p className="text-[10px] text-indigo-500 animate-pulse font-medium">
              {t.gpsAcquiring}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {!isCustomRadius ? (
            <select
              value={radiusInput}
              onChange={(e) => {
                if (e.target.value === "custom") {
                  setIsCustomRadius(true);
                  setRadiusInput("");
                } else {
                  setRadiusInput(e.target.value);
                }
              }}
              className="px-3 py-1.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-xs font-bold text-gray-700 dark:text-gray-200 shadow-sm focus:outline-none cursor-pointer hover:border-indigo-500 dark:hover:border-indigo-400 transition-all"
            >
              <option value="2">2 {language === 'hi' ? 'किमी' : 'km'}</option>
              <option value="5">5 {language === 'hi' ? 'किमी' : 'km'}</option>
              <option value="10">10 {language === 'hi' ? 'किमी' : 'km'}</option>
              <option value="20">20 {language === 'hi' ? 'किमी' : 'km'}</option>
              <option value="custom">{language === 'hi' ? 'कस्टम...' : 'Custom...'}</option>
            </select>
          ) : (
            <div className="relative flex items-center">
              <input
                type="text"
                value={radiusInput}
                onChange={(e) => setRadiusInput(e.target.value)}
                placeholder={language === 'hi' ? "जैसे: 3.5 किमी, 30 किमी" : "e.g. 3.5km, 30km"}
                className="w-28 px-3 py-1.5 pr-8 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-750 rounded-xl text-xs font-bold text-gray-700 dark:text-gray-200 shadow-sm focus:outline-none"
              />
              <button
                type="button"
                onClick={() => {
                  setIsCustomRadius(false);
                  setRadiusInput("10");
                }}
                className="absolute right-2 px-1.5 py-0.5 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 font-bold cursor-pointer"
                title="Back to options"
              >
                ✕
              </button>
            </div>
          )}
        </div>
      </div>

      <button
        onClick={handleSearch}
        disabled={isLoading || locState === 'fetching'}
        className="w-full py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-bold flex items-center justify-center gap-2 transition-all cursor-pointer"
      >
        <FaSearch />
        <span>{isLoading ? t.searchingGooglePlaces : t.btnSearchDoctors.replace('{specialist}', translatedSpecialist)}</span>
      </button>

      {doctors && doctors.length > 0 ? (
        <div className="flex flex-col gap-4 mt-2">
          <h3 className="text-sm font-bold text-gray-400 uppercase text-left">{t.recommendedDoctorsHeader}</h3>
          {doctors.map((doc, idx) => (
            <div key={idx} className="p-4 bg-gray-50 dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-855 text-left">
              <div className="flex justify-between items-start gap-2">
                <div>
                  <h4 className="font-bold text-gray-800 dark:text-gray-100">{doc.name}</h4>
                  <span className="inline-block mt-1 text-[10px] text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full font-bold uppercase">
                    {doc.specialty_tag}
                  </span>
                </div>
                <div className="flex items-center gap-1 text-yellow-600 text-xs font-bold bg-yellow-50 px-2 py-1 rounded">
                  <FaStar />
                  <span>{doc.rating?.toFixed(1) || "4.5"}</span>
                </div>
              </div>

              <p className="text-xs text-gray-500 mt-2">{doc.address}</p>
              
              <div className="flex justify-between items-center mt-3 pt-3 border-t border-gray-100 dark:border-gray-800 text-xs font-semibold">
                <span className="text-gray-400 font-medium">
                  {t.distanceLabel}: <span className="text-indigo-600 font-bold">{doc.distance_km?.toFixed(1)} {language === 'hi' ? 'किमी' : 'km'}</span>
                </span>

                <div className="flex gap-2">
                  {doc.phone_number && (
                    <a href={`tel:${doc.phone_number}`} className="p-2 bg-gray-100 dark:bg-gray-800 text-gray-600 rounded-lg">
                      <FaPhoneAlt />
                    </a>
                  )}
                  <a href={doc.directions_url} target="_blank" rel="noreferrer" className="px-3 py-1.5 bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 rounded-lg flex items-center gap-1 text-xs">
                    <FaDirections />
                    <span>{t.btnMap}</span>
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        !isLoading && <p className="text-xs text-gray-400">{t.resultsPlaceholder}</p>
      )}
    </div>
  );
}