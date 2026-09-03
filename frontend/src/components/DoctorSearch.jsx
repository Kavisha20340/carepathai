import React, { useState, useEffect } from 'react';
import { FaMapMarkerAlt, FaSearch, FaStar, FaPhoneAlt, FaDirections } from 'react-icons/fa';
import { useStore } from '../store/useStore';
import { translations, specialistTranslations } from '../utils/translations';

export default function DoctorSearch() {
  const { triageResult, doctors, searchDoctors, isLoading, setError, language } = useStore();
  const [radius, setRadius] = useState(10.0);
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
    await searchDoctors(triageResult.specialist_type, coords.lat, coords.lng, parseFloat(radius));
  };

  if (!triageResult) return null;

  const specialist_type = triageResult.specialist_type;
  const translatedSpecialist = sT[specialist_type] || specialist_type;

  return (
    <div className="w-full max-w-2xl mx-auto mt-8 flex flex-col gap-6 p-6 bg-white dark:bg-gray-800 rounded-3xl shadow-xl border border-gray-150 dark:border-gray-700">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-gray-150 dark:border-gray-700 text-left">
        <div>
          <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100 flex items-center gap-2">
            <FaMapMarkerAlt className="text-indigo-600" />
            <span>{t.stepSearchNearby}</span>
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {locState === 'success' ? t.gpsSuccess : t.gpsAcquiring}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold text-gray-400">{t.radiusLabel}</label>
          <select
            value={radius}
            onChange={(e) => setRadius(parseFloat(e.target.value))}
            className="px-2 py-1 bg-gray-50 dark:bg-gray-900 border border-gray-200 rounded text-sm font-bold text-gray-700 dark:text-gray-300 focus:outline-none"
          >
            <option value="2.0">2 km</option>
            <option value="5.0">5 km</option>
            <option value="10.0">10 km</option>
            <option value="20.0">20 km</option>
          </select>
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
                  {t.distanceLabel}: <span className="text-indigo-600 font-bold">{doc.distance_km?.toFixed(1)} km</span>
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