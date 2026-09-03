import React, { useState, useRef } from 'react'
import { FaMicrophone, FaStop, FaPaperPlane, FaExclamationTriangle } from 'react-icons/fa'
import { useStore } from '../store/useStore'

export default function MicInput() {
  const { isLoading, transcribeAudio, submitTriageTurn, error, setError, setIsRecording, language } = useStore()
  const [textInput, setTextInput] = useState('')
  const [recordState, setRecordState] = useState('idle') // idle, starting, recording, stopping
  const mediaRecorderRef = useRef(null)
  const streamRef = useRef(null)
  const audioChunksRef = useRef([])

  const startRecording = async () => {
    setError(null)
    setRecordState('starting')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const options = MediaRecorder.isTypeSupported('audio/webm') ? { mimeType: 'audio/webm' } : {}
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
        setRecordState('stopping')
        const blob = new Blob(audioChunksRef.current, { type: mediaRecorder.mimeType || 'audio/webm' })
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(t => t.stop())
          streamRef.current = null
        }
        if (blob.size > 0) {
          try {
            const txt = await transcribeAudio(blob)
            if (txt) await submitTriageTurn(txt)
          } catch (e) { console.error(e) }
        } else {
          setError("No audio captured.")
        }
        setRecordState('idle')
        setIsRecording(false)
      }
      mediaRecorder.start(250)
      setRecordState('recording')
      setIsRecording(true)
    } catch (err) {
      console.error(err)
      setError("Unable to access microphone.")
      resetRecorder()
    }
  }

  const stopRecording = () => {
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
    btnLabel = isHindi ? 'ऑडियो सेव हो रहा है...' : 'Saving audio...' 
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

      {error && (
        <div className="mt-4 flex gap-2 p-3 bg-red-50 text-red-700 rounded-xl text-sm">
          <FaExclamationTriangle className="mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}