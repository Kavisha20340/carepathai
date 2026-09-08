import { translations, specialistTranslations, slotValueTranslations } from './translations';

const getTranslatedSlotVal = (val, lang) => {
  if (val === null || val === undefined) return '';
  const strVal = val.toString();
  if (lang !== 'hi') return strVal;
  const keyLower = strVal.toLowerCase().trim();
  const dict = typeof slotValueTranslations !== 'undefined' ? slotValueTranslations : {};
  return dict[keyLower] || strVal;
};

export const generateAndPrintReport = ({
  sessionId,
  language,
  conversationHistory,
  triageResult,
  sessionState,
  onReportGenerated
}) => {
  const lang = language || 'en';
  const t = translations[lang] || translations.en;
  const sT = specialistTranslations[lang] || specialistTranslations.en;
  const isHindi = lang === 'hi';

  const filteredHistory = (conversationHistory || []).filter((msg, idx) => !(idx === 0 && msg.role === 'assistant'));

  let dialogueTextTrace = "";
  const dialogueHtmlList = filteredHistory.map((msg) => {
    const isUser = msg.role === 'user';
    const roleLabel = isUser ? (isHindi ? 'मरीज़ (Patient)' : 'Patient') : (isHindi ? 'केयरपाथ एआई (Assistant)' : 'CarePathAI');
    const timeStr = new Date(msg.timestamp || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    dialogueTextTrace += `[${timeStr}] ${roleLabel}: ${msg.text}\n`;
    return `<div style="margin-bottom:8px;padding:8px 12px;border-radius:8px;background:${isUser ? '#f0fdf4' : '#f8fafc'};border-left:4px solid ${isUser ? '#10b981' : '#6366f1'};border:1px solid #e2e8f0;"><div style="display:flex;justify-content:space-between;margin-bottom:2px;"><span style="font-weight:700;font-size:11px;color:${isUser ? '#047857' : '#4338ca'};">${roleLabel}</span><span style="font-size:10px;color:#94a3b8;">${timeStr}</span></div><div style="font-size:12px;color:#1e293b;line-height:1.4;">${msg.text}</div></div>`;
  }).join('');

  const urgencyLabel = { self_care: t.self_care, routine: t.routine, urgent: t.urgent, emergency: t.emergency }[triageResult?.urgency_level] || triageResult?.urgency_level || '';
  const specialistLabel = sT[triageResult?.specialist_type] || triageResult?.specialist_type || '';
  const confidenceLabel = { high: t.high, moderate: t.moderate, low: t.low }[triageResult?.confidence] || triageResult?.confidence || '';

  const slotLabels = { chief_complaint: t.chiefComplaint, body_location: t.bodyLocation, onset: t.onset, duration: t.duration, severity: t.severity, associated_symptoms: t.associatedSymptoms, aggravating_factors: t.aggravatingFactors };

  let slotsHtmlList = '', slotsTextTrace = '';
  if (sessionState) {
    Object.entries(sessionState).forEach(([key, val]) => {
      if (key === 'red_flags_present' || key === 'relevant_history') return;
      const isFilled = val !== null && val !== undefined && (!Array.isArray(val) || val.length > 0);
      let displayVal = t.notCaptured || 'Not Captured';
      if (isFilled) displayVal = Array.isArray(val) ? val.map(i => getTranslatedSlotVal(i, lang)).join(', ') : getTranslatedSlotVal(val, lang);
      const label = slotLabels[key] || key;
      slotsTextTrace += `• ${label}: ${displayVal}\n`;
      slotsHtmlList += `<div style="padding:8px 10px;background:#f8fafc;border-radius:6px;border:1px solid #e2e8f0;"><div style="font-size:10px;font-weight:700;color:#64748b;text-transform:uppercase;">${label}</div><div style="font-size:12px;font-weight:700;color:${isFilled ? '#4f46e5' : '#94a3b8'};margin-top:2px;">${displayVal}</div></div>`;
    });
  }
  const fullRawReportTrace = `CAREPATH AI REPORT\nSession ID: ${sessionId}\nTimestamp: ${new Date().toLocaleString()}\nLanguage: ${lang}\n\n1. DIALOGUE:\n${dialogueTextTrace}\n2. ASSESSMENT:\n• ${t.urgencyLevel}: ${urgencyLabel}\n• ${t.specialistType}: ${specialistLabel}\n• ${t.confidence}: ${confidenceLabel}\n${t.clinicalReasoning}:\n${triageResult?.reasoning_summary || ''}\n\n3. METADATA:\n${slotsTextTrace}`.trim();

  if (onReportGenerated && typeof onReportGenerated === 'function') {
    onReportGenerated(fullRawReportTrace);
  }

  const originalDocTitle = document.title;
  const targetFilename = `carepathai_${sessionId}`;
  document.title = targetFilename;

  const title = isHindi ? "केयरपाथ एआई - प्राथमिक चिकित्सा मूल्यांकन" : "CarePathAI - Clinical Triage Assessment Report";
  const css = "@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');@page{margin:12mm;size:auto;}body{font-family:'Plus Jakarta Sans','Noto Sans Devanagari',sans-serif;padding:16px;color:#0f172a;max-width:750px;margin:0 auto;line-height:1.4;background:#fff;}.header{text-align:center;border-bottom:2px solid #6366f1;padding-bottom:12px;margin-bottom:16px;}.logo{font-size:24px;font-weight:800;color:#4f46e5;}.subtitle{font-size:12px;font-weight:600;color:#64748b;margin-top:2px;}.meta-bar{display:flex;justify-content:space-between;background:#f8fafc;padding:8px 12px;border-radius:8px;border:1px solid #e2e8f0;font-size:10px;font-weight:600;color:#475569;margin-bottom:16px;}.section-title{font-size:12px;font-weight:800;color:#4f46e5;text-transform:uppercase;border-bottom:1px solid #cbd5e1;padding-bottom:4px;margin-top:16px;margin-bottom:8px;}.grid-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px;}.badge-box{padding:8px;border-radius:8px;border:1px solid #e2e8f0;background:#f8fafc;text-align:center;}.badge-label{font-size:9px;font-weight:700;color:#64748b;text-transform:uppercase;}.badge-val{font-size:13px;font-weight:800;color:#1e293b;margin-top:2px;}.reasoning-box{padding:12px;border-radius:8px;background:#eef2ff;border:1px solid #c7d2fe;margin-bottom:16px;}.reasoning-title{font-size:11px;font-weight:800;color:#3730a3;margin-bottom:4px;}.reasoning-text{font-size:12px;font-weight:600;color:#1e1b4b;}.slot-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;}";

  let iframe = document.getElementById('carepath_print_iframe');
  if (!iframe) {
    iframe = document.createElement('iframe');
    iframe.id = 'carepath_print_iframe';
    iframe.style.position = 'fixed';
    iframe.style.right = '0';
    iframe.style.bottom = '0';
    iframe.style.width = '0';
    iframe.style.height = '0';
    iframe.style.border = '0';
    iframe.style.visibility = 'hidden';
    document.body.appendChild(iframe);
  }

  const iframeDoc = iframe.contentWindow.document;
  iframeDoc.open();
  iframeDoc.write(`<!DOCTYPE html><html lang="${lang}"><head><meta charset="utf-8"/><title>${targetFilename}</title><style>${css}</style></head><body><div class="header"><div class="logo">CarePathAI</div><div class="subtitle">${title}</div></div><div class="meta-bar"><span><strong>Session ID:</strong> ${sessionId}</span><span><strong>Date:</strong> ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</span></div><div class="section-title">${isHindi ? "1. लक्षण बातचीत का विवरण" : "1. Patient Intake Dialogue"}</div><div style="display:flex;flex-direction:column;gap:6px;margin-bottom:16px;">${dialogueHtmlList}</div><div class="section-title">${isHindi ? "2. सटीक लक्षण विश्लेषण" : "2. Symptom Capture Analysis"}</div><div class="grid-3"><div class="badge-box"><div class="badge-label">${t.urgencyLevel}</div><div class="badge-val" style="color:#4338ca;">${urgencyLabel}</div></div><div class="badge-box"><div class="badge-label">${t.specialistType}</div><div class="badge-val" style="color:#047857;">${specialistLabel}</div></div><div class="badge-box"><div class="badge-label">${t.confidence}</div><div class="badge-val">${confidenceLabel}</div></div></div><div class="reasoning-box"><div class="reasoning-title">${t.clinicalReasoning}</div><div class="reasoning-text">${triageResult?.reasoning_summary || ''}</div></div><div class="section-title">${isHindi ? "3. लक्षणों का विवरण" : "3. Symptom Summary"}</div><div class="slot-grid">${slotsHtmlList}</div></body></html>`);
  iframeDoc.close();

  setTimeout(() => {
    iframe.contentWindow.focus();
    iframe.contentWindow.print();
    setTimeout(() => {
      document.title = originalDocTitle;
    }, 1000);
  }, 250);
};
