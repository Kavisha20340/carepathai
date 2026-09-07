import { create } from 'zustand'
import axios from 'axios'
import { translations } from '../utils/translations'

// API Base URL - points to our deployed backend or falls back to local development
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

// Common headers for our requests - using the developer mock token bypass
const getHeaders = () => ({
  'Authorization': 'Bearer mock_token_abc',
})

// Generate a random session ID
const generateSessionId = () => {
  return 'sess_' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)
}

// Get initial language and greeting from localStorage for Session Recovery
const getInitialLanguage = () => {
  return localStorage.getItem('carepath_lang') || null
}

const getInitialGreeting = (lang) => {
  if (!lang) return []
  const greeting = lang === 'hi'
    ? "CarePathAI में आपका स्वागत है! संक्षेप में अपने लक्षणों का वर्णन करें और हम आपको उच्च-रेटेड स्थानीय विशेषज्ञों के पास निर्देशित करेंगे।"
    : "Welcome to CarePathAI! Briefly describe your symptoms and we will guide you to highly-rated local specialists."
  return [
    {
      role: 'assistant',
      text: greeting,
      timestamp: Date.now()
    }
  ]
}

const restoredLang = getInitialLanguage()

export const useStore = create((set, get) => ({
  // Core Session State
  sessionId: generateSessionId(),
  language: restoredLang, // 'en' or 'hi'
  turnCount: 0,
  maxTurns: 3,
  sessionState: {
    chief_complaint: null,
    body_location: null,
    onset: null,
    duration: null,
    severity: null,
    associated_symptoms: [],
    aggravating_factors: null,
    relevant_history: null,
    red_flags_present: []
  },
  conversationHistory: getInitialGreeting(restoredLang),
  triageResult: null,
  triageResultCache: { en: null, hi: null },
  doctors: [],

  // UI/UX Statuses
  isLoading: false,
  isDoctorsLoading: false,
  isRecording: false,
  error: null,
  emergencyMessage: null,

  // Reset Session for a fresh start
  resetSession: (clearLanguage = false) => {
    const lang = clearLanguage ? null : get().language
    if (clearLanguage) {
      localStorage.removeItem('carepath_lang')
    }
    
    set({
      sessionId: generateSessionId(),
      language: lang,
      turnCount: 0,
      sessionState: {
        chief_complaint: null,
        body_location: null,
        onset: null,
        duration: null,
        severity: null,
        associated_symptoms: [],
        aggravating_factors: null,
        relevant_history: null,
        red_flags_present: []
      },
      conversationHistory: getInitialGreeting(lang),
      triageResult: null,
      triageResultCache: { en: null, hi: null },
      doctors: [],
      isLoading: false,
      isDoctorsLoading: false,
      isRecording: false,
      error: null,
      emergencyMessage: null,
    })
  },

  // Actions
  setLanguage: async (lang) => {
    localStorage.setItem('carepath_lang', lang);
    const { sessionId, triageResult, conversationHistory, triageResultCache } = get();

    // Set language immediately in state so UI headers and static elements toggle instantly
    set({ language: lang });

    if (triageResult) {
      // Check dual-language in-memory cache
      const cached = triageResultCache ? triageResultCache[lang] : null;
      if (cached && cached.triageResult && cached.sessionState) {
        // Cache HIT: Switch immediately in 0ms without network call or loading shimmer!
        set({
          triageResult: cached.triageResult,
          sessionState: cached.sessionState,
          isLoading: false
        });
        return;
      }

      // Cache MISS: Fetch translation once from backend and cache it
      set({ isLoading: true });
      try {
        const response = await axios.post(`${API_BASE_URL}/translate-results?session_id=${sessionId}&language=${lang}`, {}, {
          headers: getHeaders()
        });

        // Session Guard Check: Discard if session was reset while request was in-flight
        if (sessionId !== get().sessionId) {
          console.log("Discarding stale translation response from previous session:", sessionId);
          return;
        }

        const translatedTriageResult = response.data.triage_result;
        const translatedSessionState = response.data.updated_session_state;

        set((state) => ({
          triageResult: translatedTriageResult,
          sessionState: translatedSessionState,
          triageResultCache: {
            ...state.triageResultCache,
            [lang]: {
              triageResult: translatedTriageResult,
              sessionState: translatedSessionState
            }
          },
          isLoading: false
        }));
      } catch (error) {
        if (sessionId !== get().sessionId) return;
        console.error("Translation error:", error);
        set({ isLoading: false });
      }
    } else {
      if (!conversationHistory || conversationHistory.length <= 1) {
        const greeting = lang === 'hi'
          ? "CarePathAI में आपका स्वागत है! संक्षेप में अपने लक्षणों का वर्णन करें और हम आपको उच्च-रेटेड स्थानीय विशेषज्ञों के पास निर्देशित करेंगे।"
          : "Welcome to CarePathAI! Briefly describe your symptoms and we will guide you to highly-rated local specialists.";
        
        set({
          conversationHistory: [
            {
              role: 'assistant',
              text: greeting,
              timestamp: Date.now()
            }
          ]
        });
      }
    }
  },

  setIsRecording: (isRecording) => set({ isRecording }),
  setError: (error) => set({ error }),
  setEmergencyMessage: (msg) => set({ emergencyMessage: msg }),

  // 1. Transcribe audio to text
  transcribeAudio: async (audioBlob) => {
    const requestSessionId = get().sessionId;
    set({ isLoading: true, error: null })
    try {
      const formData = new FormData()
      formData.append('file', audioBlob, 'audio.webm')

      const response = await axios.post(`${API_BASE_URL}/transcribe?language=${get().language}&session_id=${requestSessionId}`, formData, {
        headers: {
          ...getHeaders(),
          'Content-Type': 'multipart/form-data',
        }
      })

      // Session Guard Check: Discard if session was reset while request was in-flight
      if (requestSessionId !== get().sessionId) {
        console.log("Discarding stale transcription response from previous session:", requestSessionId);
        return null;
      }

      const transcript = response.data.transcript
      if (!transcript || transcript.trim() === '') {
        const lang = get().language || 'en'
        const errMsg = translations[lang]?.errNoSpeech || translations.en.errNoSpeech
        throw new Error(errMsg)
      }

      set({ isLoading: false })
      return transcript
    } catch (err) {
      if (requestSessionId !== get().sessionId) return null;
      console.error("Transcription error:", err)
      const errMsg = err.response?.data?.detail || err.message || "Failed to transcribe audio. Please try typing or recording again."
      set({ isLoading: false, error: errMsg })
      throw err
    }
  },

  // 2. Submit transcript to triage endpoint
  submitTriageTurn: async (transcript) => {
    const requestSessionId = get().sessionId;
    set({ isLoading: true, error: null })
    const { turnCount, maxTurns, language } = get()
    const nextTurn = turnCount + 1

    // Append user message immediately to the conversation history
    set((state) => ({
      conversationHistory: [
        ...state.conversationHistory,
        { role: 'user', text: transcript, timestamp: Date.now() }
      ],
      turnCount: nextTurn
    }))

    try {
      const response = await axios.post(`${API_BASE_URL}/triage`, {
        transcript,
        session_id: requestSessionId,
        turn_count: nextTurn,
        max_turns: maxTurns,
        language: language
      }, {
        headers: getHeaders()
      })

      // Session Guard Check: Discard if session was reset while request was in-flight
      if (requestSessionId !== get().sessionId) {
        console.log("Discarding stale triage response from previous session:", requestSessionId);
        return;
      }

      const data = response.data
      console.log("Triage API response:", data)

      if (data.status === 'emergency') {
        set({
          emergencyMessage: data.message,
          isLoading: false
        })
        return
      }

      if (data.status === 'follow_up') {
        set((state) => {
          const history = state.conversationHistory.map((item) => ({ ...item }));
          if (data.denoised_transcript) {
            for (let i = history.length - 1; i >= 0; i--) {
              if (history[i].role === 'user') {
                history[i].text = data.denoised_transcript;
                break;
              }
            }
          }
          return {
            sessionState: data.updated_session_state,
            conversationHistory: [
              ...history,
              { role: 'assistant', text: data.follow_up_question, timestamp: Date.now() }
            ],
            isLoading: false
          };
        })
      } else if (data.status === 'triage_complete') {
        const currentLang = get().language || 'en';
        set((state) => {
          const history = state.conversationHistory.map((item) => ({ ...item }));
          if (data.denoised_transcript) {
            for (let i = history.length - 1; i >= 0; i--) {
              if (history[i].role === 'user') {
                history[i].text = data.denoised_transcript;
                break;
              }
            }
          }
          return {
            sessionState: data.updated_session_state,
            conversationHistory: history,
            triageResult: data.triage_result,
            triageResultCache: {
              ...state.triageResultCache,
              [currentLang]: {
                triageResult: data.triage_result,
                sessionState: data.updated_session_state
              }
            },
            isLoading: false
          };
        });
      }
    } catch (err) {
      if (requestSessionId !== get().sessionId) return;
      console.error("Triage error:", err)
      const errMsg = err.response?.data?.detail || err.message || "Triage processing failed. Please try again."
      set({ isLoading: false, error: errMsg })
    }
  },

  // 3. Search for nearby doctors
  searchDoctors: async (specialistType, lat, lng, radiusKm = 10.0, minRating = 0.0, maxRating = 5.0) => {
    const requestSessionId = get().sessionId;
    set({ isDoctorsLoading: true, error: null })
    try {
      const response = await axios.post(`${API_BASE_URL}/doctors`, {
        specialist_type: specialistType,
        lat,
        lng,
        radius_km: radiusKm,
        max_results: 8,
        min_rating: parseFloat(minRating),
        max_rating: parseFloat(maxRating)
      }, {
        headers: getHeaders()
      })

      // Session Guard Check: Discard if session was reset while request was in-flight
      if (requestSessionId !== get().sessionId) {
        console.log("Discarding stale doctors search response from previous session:", requestSessionId);
        return;
      }

      set({
        doctors: response.data.doctors || [],
        isDoctorsLoading: false
      })
    } catch (err) {
      if (requestSessionId !== get().sessionId) return;
      console.error("Doctors search error:", err)
      const errMsg = err.response?.data?.detail || err.message || "Failed to search doctors. Please try again."
      set({ isDoctorsLoading: false, error: errMsg })
    }
  }
}))
