export function speakOnHover(element: HTMLElement | null, text: string) {
  if (!element || typeof window === "undefined") return;
  const handler = () => {
    try {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.95;
      utterance.pitch = 1;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
    } catch (error) {
      console.warn('TTS error:', error);
    }
  };
  element.addEventListener("mouseenter", handler);
  return () => element.removeEventListener("mouseenter", handler);
}

export function speakText(text: string, options?: { rate?: number; pitch?: number; volume?: number }) {
  if (typeof window === "undefined") return;
  try {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = options?.rate || 0.95;
    utterance.pitch = options?.pitch || 1;
    utterance.volume = options?.volume || 1;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  } catch {}
}

export function playAudioFeedback(type: 'success' | 'error' | 'click' | 'notification') {
  if (typeof window === "undefined") return;
  
  // Create audio context for simple beep sounds
  const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
  const oscillator = audioContext.createOscillator();
  const gainNode = audioContext.createGain();
  
  oscillator.connect(gainNode);
  gainNode.connect(audioContext.destination);
  
  // Different frequencies for different feedback types
  const frequencies = {
    success: 800,
    error: 300,
    click: 600,
    notification: 1000
  };
  
  oscillator.frequency.setValueAtTime(frequencies[type], audioContext.currentTime);
  oscillator.type = 'sine';
  
  gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
  gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
  
  oscillator.start(audioContext.currentTime);
  oscillator.stop(audioContext.currentTime + 0.1);
}


