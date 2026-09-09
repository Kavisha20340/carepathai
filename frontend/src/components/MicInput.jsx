import React, { useState, useRef, useEffect } from 'react'
import { FaMicrophone, FaStop, FaPaperPlane, FaExclamationTriangle } from 'react-icons/fa'
import { useStore } from '../store/useStore'
import { translations } from '../utils/translations'

export default function MicInput() {
  const { isLoading, transcribeAudio, submitTriageTurn, error, setError, setIsRecording, language } = useStore()
  const [textInput, setTextInput] = useState('')
  const [recordState, setRecordState] = useState('idle') // idle, starting, recording, stopping
  const mediaRecorderRef = useRef(null)
  const streamRef = useRef(null)
  const audioChunksRef = useRef([])
  const maxRecordingTimerRef = useRef(null)
  const isDurationExceededRef = useRef(false)

  const isModalError = 
    error === translations.en.errNoSpeech || error === translations.hi.errNoSpeech ||
    error === translations.en.errMaxDuration || error === translations.hi.errMaxDuration

  useEffect(() => {
    if (isModalError) {
      const timer = setTimeout(() => {
        setError(null)
      }, 2500) // Auto-dismiss error modal after 2.5 seconds
      return () => clearTimeout(timer)
    }
  }, [error, isModalError, setError])

  useEffect(() => {
    return () => {
      if (maxRecordingTimerRef.current) clearTimeout(maxRecordingTimerRef.current)
    }
  }, [])

  const startRecording = async () => {
    setError(null)
    setRecordState('starting')
    isDurationExceededRef.current = false

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 2,
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false
        }
      })
      streamRef.current = stream
      const options = MediaRecorder.isTypeSupported('audio/webm') 
        ? { mimeType: 'audio/webm', audioBitsPerSecond: 128000 } 
        : { audioBitsPerSecond: 128000 }
      const mediaRecorder = new MediaRecorder(stream, options)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) audioChunksRef.current.push(e.data)
      }
      mediaRecorder.onerror = () => {
        setError("Recording failed.")
        resetRecorder()
      }
      mediaRecorder.onstop = async () => {
        if (maxRecordingTimerRef.current) {
          clearTimeout(maxRecordingTimerRef.current)
          maxRecordingTimerRef.current = null
        }

        // If recording reached the 55-second threshold, discard audio and show 1-minute limit warning modal
        if (isDurationExceededRef.current) {
          isDurationExceededRef.current = false
          if (streamRef.current) {
            streamRef.current.getTracks().forEach(t => t.stop())
            streamRef.current = null
          }
          audioChunksRef.current = []
          setRecordState('idle')
          setIsRecording(false)

          const lang = language || 'en'
          const errMsg = translations[lang]?.errMaxDuration || translations.en.errMaxDuration
          setError(errMsg)
          return
        }

        setRecordState('stopping')
        const blob = new Blob(audioChunksRef.current, { type: mediaRecorder.mimeType || 'audio/webm' })
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(t => t.stop())
          streamRef.current = null
        }
        if (blob.size > 0) {
          try {
            const txt = await transcribeAudio(blob)
            setRecordState('idle')
            if (txt) await submitTriageTurn(txt)
          } catch (e) { 
            console.error(e) 
            setRecordState('idle')
          }
        } else {
          setError("No audio captured.")
          setRecordState('idle')
        }
        setIsRecording(false)
      }
      mediaRecorder.start(250)
      setRecordState('recording')
      setIsRecording(true)

      // Set 55-second safety timer (55,000ms) to trigger 1-minute limit reset before GCP STT limit
      if (maxRecordingTimerRef.current) clearTimeout(maxRecordingTimerRef.current)
      maxRecordingTimerRef.current = setTimeout(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          console.log("Recording duration reached 55s threshold. Discarding audio and triggering 1-minute limit warning.")
          isDurationExceededRef.current = true
          stopRecording()
        }
      }, 55000)
    } catch (err) {
      console.error(err)
      setError("Unable to access microphone.")
      resetRecorder()
    }
  }

  const stopRecording = () => {
    if (maxRecordingTimerRef.current) {
      clearTimeout(maxRecordingTimerRef.current)
      maxRecordingTimerRef.current = null
    }
    setRecordState('stopping')
    try {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop()
      } else {
        resetRecorder()
      }
    } catch (err) {
      console.error(err)
      resetRecorder()
    }
  }

  const resetRecorder = () => {
    isDurationExceededRef.current = false
    if (maxRecordingTimerRef.current) {
      clearTimeout(maxRecordingTimerRef.current)
      maxRecordingTimerRef.current = null
    }
    try {
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop())
    } catch (e) { console.error(e) }
    streamRef.current = null
    mediaRecorderRef.current = null
    setRecordState('idle')
    setIsRecording(false)
  }

  const handleTextSubmit = async (e) => {
    e.preventDefault()
    if (!textInput.trim() || isLoading || recordState !== 'idle') return
    const text = textInput.trim()
    setTextInput('')
    setError(null)
    await submitTriageTurn(text)
  }

  const isBtnDisabled = isLoading || recordState === 'starting' || recordState === 'stopping'
  const isHindi = language === 'hi'
  
  let btnColor = 'bg-indigo-600'
  let btnLabel = isHindi ? 'लक्षण बताने के लिए बोलें' : 'Tap to speak symptoms'
  
  if (recordState === 'starting') { 
    btnColor = 'bg-yellow-500 animate-pulse'
    btnLabel = isHindi ? 'माइक्रोफोन चालू हो रहा है...' : 'Waking up microphone...' 
  }
  else if (recordState === 'recording') { 
    btnColor = 'bg-red-500'
    btnLabel = isHindi ? 'रिकॉर्डिंग... रोकने के लिए क्लिक करें' : 'Recording... Click to Stop' 
  }
  else if (recordState === 'stopping') { 
    btnColor = 'bg-gray-400 animate-pulse'
    btnLabel = isHindi ? 'ऑडियो प्रोसेस हो रहा है...' : 'Processing audio...' 
  }
  else if (isLoading) { 
    btnColor = 'bg-gray-400'
    btnLabel = isHindi ? 'लक्षणों का विश्लेषण हो रहा है...' : 'Analyzing symptoms...' 
  }

  return (
    <div className="w-full border-t border-gray-100 dark:border-gray-800 bg-gray-50/20 dark:bg-gray-900/5 p-4">
      <div className="flex flex-col items-center justify-center py-3 gap-4">
        <div className="relative">
          {recordState === 'recording' && <span className="absolute -inset-2 rounded-full bg-red-500/30 animate-ping pointer-events-none"></span>}
          {isLoading && <span className="absolute -inset-2 rounded-full bg-indigo-500/30 animate-pulse pointer-events-none"></span>}
          <button
            type="button"
            onClick={recordState === 'recording' ? stopRecording : startRecording}
            disabled={isBtnDisabled}
            className={`relative z-10 w-20 h-20 rounded-full flex items-center justify-center text-white text-3xl transition-all shadow-lg ${btnColor}`}
          >
            {recordState === 'recording' ? <FaStop /> : <FaMicrophone />}
          </button>
        </div>
        <p className="font-semibold text-sm tracking-wider uppercase text-gray-500">{btnLabel}</p>
      </div>

      <form onSubmit={handleTextSubmit} className="flex gap-2 mt-4 max-w-lg mx-auto w-full">
        <input
          type="text"
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          placeholder={isHindi ? "अपने लक्षण यहाँ लिखें या माइक्रोफ़ोन दबाएँ..." : "Type your symptoms here or tap microphone..."}
          disabled={isLoading || recordState !== 'idle'}
          className="flex-grow px-4 py-3 bg-gray-50 dark:bg-gray-900 border border-gray-200 rounded-xl focus:outline-none text-gray-800 dark:text-gray-200"
        />
        <button
          type="submit"
          disabled={!textInput.trim() || isLoading || recordState !== 'idle'}
          className="px-5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white rounded-xl flex items-center justify-center"
        >
          <FaPaperPlane />
        </button>
      </form>

      {error && isModalError && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-xl max-w-sm w-full border border-gray-100 dark:border-gray-700 text-center animate-scaleIn">
            <div className="w-12 h-12 bg-red-100 dark:bg-red-950/40 text-red-600 dark:text-red-400 rounded-full flex items-center justify-center mx-auto mb-4">
              <FaExclamationTriangle className="text-xl" />
            </div>
            <p className="text-gray-800 dark:text-gray-200 font-bold text-sm md:text-base leading-relaxed">
              {error}
            </p>
          </div>
        </div>
      )}

      {error && !isModalError && (
        <div className="mt-4 flex gap-2 p-3 bg-red-50 text-red-700 rounded-xl text-sm">
          <FaExclamationTriangle className="mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}