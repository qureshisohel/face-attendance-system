/**
 * FAS Camera Module — works on desktop & mobile
 * Usage: new FASCam(options)
 */
class FASCam {
  constructor(opts) {
    this.videoEl   = document.getElementById(opts.videoId || 'video');
    this.canvasEl  = document.getElementById(opts.canvasId || 'snapCanvas');
    this.overlayEl = document.getElementById(opts.overlayId || 'camOverlay');
    this.fboxEl    = document.getElementById(opts.fboxId || 'faceBox');
    this.scanEl    = document.getElementById(opts.scanId || 'scanLine');
    this.stream    = null;
    this.onCapture = opts.onCapture || null; // callback(dataUrl)
  }

  async start() {
    const constraints = {
      video: {
        facingMode: 'user',
        width: { ideal: 1280 },
        height: { ideal: 720 }
      },
      audio: false
    };
    try {
      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.videoEl.srcObject = this.stream;
      await this.videoEl.play();
      if (this.overlayEl) this.overlayEl.style.display = 'none';
      if (this.fboxEl)    this.fboxEl.style.display = 'block';
      if (this.scanEl)    this.scanEl.style.display  = 'block';
      return true;
    } catch (e) {
      alert('Camera error: ' + e.message + '\n\nMake sure:\n1. You allowed camera access\n2. No other app is using camera\n3. Using HTTPS or localhost');
      return false;
    }
  }

  stop() {
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
    }
    this.videoEl.srcObject = null;
    if (this.overlayEl) this.overlayEl.style.display = 'flex';
    if (this.fboxEl)    this.fboxEl.style.display = 'none';
    if (this.scanEl)    this.scanEl.style.display  = 'none';
  }

  capture() {
    if (!this.stream) return null;
    const c = this.canvasEl;
    c.width  = this.videoEl.videoWidth  || 640;
    c.height = this.videoEl.videoHeight || 480;
    c.getContext('2d').drawImage(this.videoEl, 0, 0);
    const dataUrl = c.toDataURL('image/jpeg', 0.88);
    if (this.onCapture) this.onCapture(dataUrl);
    return dataUrl;
  }

  isActive() { return !!this.stream; }
}
