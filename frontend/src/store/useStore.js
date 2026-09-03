import { create } from 'zustand'
import axios from 'axios'
import { translations } from '../utils/translations'

// API Base URL - points to our running local backend
const API_BASE_URL = 'http://127.0.0.1:8000'

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
  doctors: [],

  // UI/UX Statuses
  isLoading: false,
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
      doctors: [],
      isLoading: false,
      isRecording: false,
      error: null,
      emergencyMessage: null,
    })
  },

  // Actions
  setLanguage: async (lang) => {
    localStorage.setItem('carepath_lang', lang);
    const { sessionId, triageResult } = get();

    if (triageResult) {
      set({ isLoading: true });
      try {
        const response = await axios.post(`${API_BASE_URL}/translate-results?session_id=${sessionId}&language=${lang}`, {}, {
          headers: getHeaders()
        });
        set({
          language: lang,
          triageResult: response.data.triage_result,
          sessionState: response.data.updated_session_state,
          isLoading: false
        });
      } catch (error) {
        console.error("Translation error:", error);
        set({ isLoading: false, error: "Failed to translate results." });
      }
    } else {
      const greeting = lang === 'hi'
        ? "CarePathAI में आपका स्वागत है! संक्षेप में अपने लक्षणों का वर्णन करें और हम आपको उच्च-रेटेड स्थानीय विशेषज्ञों के पास निर्देशित करेंगे।"
        : "Welcome to CarePathAI! Briefly describe your symptoms and we will guide you to highly-rated local specialists.";
      
      set({
        language: lang,
        conversationHistory: [
          {
            role: 'assistant',
            text: greeting,
            timestamp: Date.now()
          }
        ]
      });
    }
  },

  setIsRecording: (isRecording) => set({ isRecording }),
  setError: (error) => set({ error }),
  setEmergencyMessage: (msg) => set({ emergencyMessage: msg }),

  // 1. Transcribe audio to text
  transcribeAudio: async (audioBlob) => {
    set({ isLoading: true, error: null })
    try {
      const formData = new FormData()
      formData.append('file', audioBlob, 'audio.webm')

      const response = await axios.post(`${API_BASE_URL}/transcribe?language=${get().language}`, formData, {
        headers: {
          ...getHeaders(),
          'Content-Type': 'multipart/form-data',
        }
      })

      const transcript = response.data.transcript
      if (!transcript || transcript.trim() === '') {
        const lang = get().language || 'en'
        const errMsg = translations[lang]?.errNoSpeech || translations.en.errNoSpeech
        throw new Error(errMsg)
      }

      set({ isLoading: false })
      return transcript
    } catch (err) {
      console.error("Transcription error:", err)
      const errMsg = err.response?.data?.detail || err.message || "Failed to transcribe audio. Please try typing or recording again."
      set({ isLoading: false, error: errMsg })
      throw err
    }
  },

  // 2. Submit transcript to triage endpoint
  submitTriageTurn: async (transcript) => {
    set({ isLoading: true, error: null })
    const { sessionId, turnCount, maxTurns, language } = get()
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
        session_id: sessionId,
        turn_count: nextTurn,
        max_turns: maxTurns,
        language: language
      }, {
        headers: getHeaders()
      })

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
        set((state) => ({
          sessionState: data.updated_session_state,
          conversationHistory: [
            ...state.conversationHistory,
            { role: 'assistant', text: data.follow_up_question, timestamp: Date.now() }
          ],
          isLoading: false
        }))
      } else if (data.status === 'triage_complete') {
        set({
          sessionState: data.updated_session_state,
          triageResult: data.triage_result,
          isLoading: false
        })
      }
    } catch (err) {
      console.error("Triage error:", err)
      const errMsg = err.response?.data?.detail || err.message || "Triage processing failed. Please try again."
      set({ isLoading: false, error: errMsg })
    }
  },

  // 3. Search for nearby doctors
  searchDoctors: async (specialistType, lat, lng, radiusKm = 10.0) => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.post(`${API_BASE_URL}/doctors`, {
        specialist_type: specialistType,
        lat,
        lng,
        radius_km: radiusKm,
        max_results: 8,
        min_rating: 4.0
      }, {
        headers: getHeaders()
      })

      set({
        doctors: response.data.doctors || [],
        isLoading: false
      })
    } catch (err) {
      console.error("Doctors search error:", err)
      const errMsg = err.response?.data?.detail || err.message || "Failed to search doctors. Please try again."
      set({ isLoading: false, error: errMsg })
    }
  }
}))
