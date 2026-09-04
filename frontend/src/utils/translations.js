export const translations = {
  en: {
    // Header & Global Controls
    logo: "CarePathAI",
    subtitle: "Voice-first AI healthcare navigator for India",
    resetBtn: "New Chat",
    sessionText: "Session",

    // Landing Page Route
    landingTitle: "Select Your Assessment Language",
    landingHindiButton: "हिंदी (Hindi)",
    landingEngButton: "English",
    landingSubtitle: "Welcome to CarepathAI. Select your preferred assessment language to begin.",
    landingHelperText: "आपके लक्षणों का आकलन करने के लिए कृपया अपनी पसंदीदा भाषा का चयन करें।",

    // Step 1: Main Conversational Triage
    assistantTitle: "Symptom Intake Assistant",
    assistantSubtitle: "Briefly describe your symptoms and we will guide you to highly-rated local specialists.",
    turnCounter: "Follow-up {turnCount} of {maxTurns}",
    initialIntake: "Initial Symptoms Intake",
    placeholderInput: "Type your symptoms here or tap microphone...",
    
    // Mic Input & Speech Labels
    btnSpeak: "Tap to speak symptoms",
    btnStarting: "Waking up microphone...",
    btnRecording: "Recording... Click to Stop",
    btnStopping: "Processing audio...",
    btnAnalyzing: "Analyzing symptoms...",
    errNoSpeech: "Speech-to-text was unable to capture any words. Please try speaking again.",

    // Step 2: Structured Results (TriageCard)
    triageSuccess: "Triage Succeeded & Saved to Firestore",
    carepathGuidance: "Your Carepath Guidance",
    carepathSubtitle: "Below is your structured symptom-fill summary followed by real-time mapped specialist doctor options.",
    cardTitle: "Symptom Capture Analysis",
    chiefComplaint: "Chief Complaint",
    bodyLocation: "Body Location",
    onset: "Onset",
    duration: "Duration",
    severity: "Severity",
    associatedSymptoms: "Associated Symptoms",
    aggravatingFactors: "Aggravating Factors",
    urgencyLevel: "Urgency Level",
    specialistType: "Recommended Specialist",
    confidence: "Confidence",
    reasoningSummary: "Reasoning Summary",
    notCaptured: "Not Captured",
    clinicalReasoning: "Clinical Reasoning Summary",
    extractedSlotMetadata: "Symptom Summary",

    // Urgency & Confidence Badges
    emergency: "Emergency",
    urgent: "Urgent",
    routine: "Routine",
    self_care: "Self Care",
    high: "High",
    moderate: "Moderate",
    low: "Low",

    // Doctor Search Screen (DoctorSearch)
    gpsSuccess: "GPS coordinates synced successfully.",
    gpsAcquiring: "Acquiring GPS coordinates...",
    stepSearchNearby: "Find Nearby Specialists",
    radiusLabel: "RADIUS:",
    btnSearchDoctors: "Find {specialist}s Near Me",
    searchingGooglePlaces: "Searching Google Places...",
    recommendedDoctorsHeader: "Recommended Doctors",
    resultsPlaceholder: "Specialist search results will appear here.",
    ratingLabel: "Rating",
    distanceLabel: "Distance",
    addressLabel: "Address",
    btnMap: "Map Directions",

    // Emergency Overlay
    criticalAlert: "Medical Emergency",
    emergencyAlertText: "This may be a medical emergency. Please call emergency services or go to the nearest ER immediately.",
    btnCall112: "Call Emergency Services (112)",
    btnRestart: "Start Over",

    // Footer
    footerText: "© {year} CarepathAI. Built for Google Patchamomma 2026.",
  },
  
  hi: {
    // Header & Global Controls
    logo: "CarePathAI",
    subtitle: "भारत के लिए वॉयस-फर्स्ट एआई हेल्थकेयर नेविगेटर",
    resetBtn: "नया चैट",
    sessionText: "सत्र",

    // Landing Page Route
    landingTitle: "अपनी भाषा का चयन करें",
    landingHindiButton: "हिंदी",
    landingEngButton: "English",
    landingSubtitle: "केयरपाथ एआई (CarepathAI) में आपका स्वागत है। आरंभ करने के लिए अपनी पसंदीदा आकलन भाषा चुनें।",
    landingHelperText: "Welcome to CarepathAI. Please select your preferred language for the symptom intake.",

    // Step 1: Main Conversational Triage
    assistantTitle: "लक्षण आकलन सहायक",
    assistantSubtitle: "संक्षेप में अपने लक्षणों का वर्णन करें और हम आपको उच्च-रेटेड स्थानीय विशेषज्ञों के पास निर्देशित करेंगे।",
    turnCounter: "सवाल {turnCount} का {maxTurns}",
    initialIntake: "प्रारंभिक लक्षण ग्रहण",
    placeholderInput: "अपने लक्षण यहाँ लिखें या माइक्रोफ़ोन दबाएँ...",
    
    // Mic Input & Speech Labels
    btnSpeak: "लक्षण बताने के लिए बोलें",
    btnStarting: "माइक्रोफोन चालू हो रहा है...",
    btnRecording: "रिकॉर्डिंग हो रही है... रोकने के लिए क्लिक करें",
    btnStopping: "ऑडियो प्रोसेस हो रहा है...",
    btnAnalyzing: "लक्षणों का विश्लेषण हो रहा है...",
    errNoSpeech: "आपकी आवाज़ पहचानी नहीं जा सकी। कृपया पुनः बोलने का प्रयास करें।",

    // Step 2: Structured Results (TriageCard)
    triageSuccess: "ट्राइएज सफल रहा और फायरस्टोर में सुरक्षित किया गया",
    carepathGuidance: "आपका केयरपाथ मार्गदर्शन",
    carepathSubtitle: "नीचे आपका संरचित लक्षण-भरने का सारांश दिया गया है, जिसके बाद वास्तविक समय में आस-पास के विशेषज्ञ डॉक्टर के विकल्प हैं।",
    cardTitle: "सटीक लक्षण विश्लेषण",
    chiefComplaint: "मुख्य शिकायत",
    bodyLocation: "शरीर का हिस्सा",
    onset: "शुरुआत",
    duration: "अवधि",
    severity: "दर्द की तीव्रता",
    associatedSymptoms: "संबंधित लक्षण",
    aggravatingFactors: "बढ़ाने वाले कारक",
    urgencyLevel: "गंभीरता/आपातकालीन स्तर",
    specialistType: "अनुशंसित विशेषज्ञ",
    confidence: "विश्वास स्तर",
    reasoningSummary: "कारण का सारांश",
    notCaptured: "उपलब्ध नहीं",
    clinicalReasoning: "चिकित्सीय तर्क का सारांश",
    extractedSlotMetadata: "लक्षणों का विवरण",

    // Urgency & Confidence Badges
    emergency: "आपातकालीन",
    urgent: "त्वरित चिकित्सा",
    routine: "सामान्य परामर्श",
    self_care: "स्वयं की देखभाल",
    high: "उच्च",
    moderate: "मध्यम",
    low: "निम्न",

    // Doctor Search Screen (DoctorSearch)
    gpsSuccess: "जीपीएस (GPS) स्थान सफलतापूर्वक सिंक हो गया है।",
    gpsAcquiring: "जीपीएस (GPS) निर्देशांक प्राप्त किए जा रहे हैं...",
    stepSearchNearby: "आस-पास के विशेषज्ञों को खोजें",
    radiusLabel: "खोज दायरा:",
    btnSearchDoctors: "मेरे पास {specialist} खोजें",
    searchingGooglePlaces: "गूगल मैप्स पर डॉक्टर खोजे जा रहे हैं...",
    recommendedDoctorsHeader: "अनुशंसित डॉक्टरों की सूची",
    resultsPlaceholder: "डॉक्टरों के खोज परिणाम यहाँ दिखाई देंगे।",
    ratingLabel: "रेटिंग",
    distanceLabel: "दूरी",
    addressLabel: "पता",
    btnMap: "नक्शा / दिशा-निर्देश",

    // Emergency Overlay
    criticalAlert: "आपातकालीन चिकित्सा",
    emergencyAlertText: "यह एक गंभीर चिकित्सा आपातकाल हो सकता है। कृपया आपातकालीन सेवाओं को कॉल करें या तुरंत नजदीकी अस्पताल के इमरजेंसी (ER) में जाएं।",
    btnCall112: "आपातकालीन सेवा (112) को कॉल करें",
    btnRestart: "नया चैट",

    // Footer
    footerText: "© {year} केयरपाथएआई। गूगल पचामोमा 2026 के लिए निर्मित।",
  }
};

export const specialistTranslations = {
  en: {
    general_physician: "General Physician",
    orthopedic: "Orthopedic",
    dermatologist: "Dermatologist",
    pulmonologist: "Pulmonologist",
    cardiologist: "Cardiologist",
    gastroenterologist: "Gastroenterologist",
    ent: "ENT Specialist",
    gynecologist: "Gynecologist",
    pediatrician: "Pediatrician",
    ophthalmologist: "Ophthalmologist",
    psychiatrist: "Psychiatrist"
  },
  hi: {
    general_physician: "सामान्य चिकित्सक",
    orthopedic: "हड्डी रोग विशेषज्ञ",
    dermatologist: "त्वचा रोग विशेषज्ञ",
    pulmonologist: "फेफड़े और श्वसन रोग विशेषज्ञ",
    cardiologist: "हृदय रोग विशेषज्ञ",
    gastroenterologist: "पेट और पाचन रोग विशेषज्ञ",
    ent: "कान, नाक, गला विशेषज्ञ",
    gynecologist: "स्त्री रोग विशेषज्ञ",
    pediatrician: "बाल रोग विशेषज्ञ",
    ophthalmologist: "नेत्र रोग विशेषज्ञ",
    psychiatrist: "मनोचिकित्सक"
  }
};

export const slotValueTranslations = {
  // Onset values
  "sudden": "अचानक",
  "gradual": "धीरे-धीरे",
  "unknown": "अज्ञात",
  // Common body locations
  "chest": "सीने (छाती)",
  "back": "पीठ",
  "knee": "घुटने",
  "knees": "घुटने",
  "skin": "त्वचा",
  "throat": "गला",
  "head": "सिर",
  "stomach": "पेट",
  "abdomen": "पेट",
  "ear": "कान",
  "nose": "नाक",
  "eye": "आँख",
  "feet": "पैर",
  "foot": "पैर",
  "leg": "टांग / पैर",
  "legs": "टांगें / पैर",
  "ankle": "टखना",
  "knees and ankles": "घुटने और टखने",
  // Common chief complaints/symptoms
  "dry cough": "सूखी खांसी",
  "cough": "खांसी",
  "back pain": "पीठ का दर्द",
  "knee pain": "घुटने का दर्द",
  "chest pain": "सीने में दर्द",
  "pain": "दर्द",
  "fever": "बुखार",
  "itching": "खुजली",
  "rash": "त्वचा पर दाने",
  "breathlessness": "सांस फूलना",
  "headache": "सिरदर्द",
  "vomiting": "उल्टी",
  "diarrhea": "दस्त",
  "acidity": "एसिडिटी",
  "gas": "गैस",
  "swelling": "सूजन",
  "scratches": "खरोंचें",
  "swelling and scratches": "सूजन और खरोंचें",
  "inability to move": "हिलने-डुलने में असमर्थता",
  // Durations
  "several hours": "कई घंटे",
  "1 week": "1 सप्ताह",
  "2 weeks": "2 सप्ताह",
  "3 weeks": "3 सप्ताह",
  "1 day": "1 दिन",
  "2 days": "2 दिन",
  "3 days": "3 दिन",
  "4 days": "4 दिन",
  "5 days": "5 दिन",
  "6 days": "6 दिन",
  "1 month": "1 महीना",
};

