import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getFirestore, doc, getDoc } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";

const firebaseConfig = { 
    apiKey: "AIzaSyCkuuMhAgsojUF1OslO7zSMrC3dKxoAo-U", 
    authDomain: "perekyprp.firebaseapp.com", 
    projectId: "perekyprp", 
    storageBucket: "perekyprp.firebasestorage.app", 
    messagingSenderId: "286165285193", 
    appId: "1:286165285193:web:36d2dfb77de7e3684e8298", 
    measurementId: "G-M18P0MG4G4" 
}; 

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

(function() {
    'use strict';

    let config = null;

    const init = async () => {
        console.log('System: Starting initialization...');
        try {
            config = await loadConfig();
            console.log('System: Config loaded');
            if (config) {
                populateContent(config);
                initBgCanvas();
                initSoundEffects();
            }
        } catch (e) {
            console.error('System: Initialization error:', e);
        } finally {
            console.log('System: Finalizing setup...');
            setupEventListeners();
            revealOnScroll();
            hidePreloader();
        }
    };

    const hidePreloader = () => {
        const preloader = document.getElementById('preloader');
        if (preloader) {
            preloader.style.opacity = '0';
            setTimeout(() => {
                preloader.style.display = 'none';
                document.body.classList.remove('loading');
                initFullscreenViewer();
            }, 800);
        }
    };

    const initFullscreenViewer = () => {
        const overlay = document.getElementById('fullscreen-overlay');
        const fsImg = document.getElementById('fullscreen-img');
        const close = document.querySelector('.close-overlay');
        
        if (!overlay || !fsImg) return;

        const openViewer = (src) => {
            fsImg.src = src;
            overlay.classList.add('active');
            document.body.style.overflow = 'hidden';
        };

        const closeViewer = () => {
            overlay.classList.remove('active');
            document.body.style.overflow = '';
        };

        document.body.addEventListener('click', (e) => {
            if (e.target.tagName === 'IMG' && (e.target.closest('.screenshot-item') || e.target.closest('.media-item') || e.target.id === 'hero-img')) {
                openViewer(e.target.src);
            }
        });

        if (close) close.addEventListener('click', closeViewer);
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeViewer();
        });
        window.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeViewer();
        });
    };

    const loadConfig = async () => {
        try {
            // 1. Try Firestore
            const docRef = doc(db, "settings", "site_config");
            const docSnap = await getDoc(docRef);
            
            if (docSnap.exists()) {
                return docSnap.data();
            }
            
            // 2. Fallback to local
            const response = await fetch('/config.json');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.warn('Firestore load failed, using local fallback:', error.message);
            try {
                const resp = await fetch('/config.json');
                return await resp.json();
            } catch(e) {
                return getFallbackConfig();
            }
        }
    };

    const getFallbackConfig = () => {
        return {
            "app_name": "MoneyTracker Pro",
            "version": "1.0.2",
            "file_size": "45.2 MB",
            "description": "Профессиональное решение для автоматизации учета финансов на базе Firebase.",
            "why_us": [
                { "icon": "fas fa-microchip", "title": "Cloud Core", "desc": "Данные всегда под рукой благодаря Firebase." }
            ]
        };
    };

    const populateContent = (config) => {
        try {
            document.querySelectorAll('.app-version').forEach(el => {
                el.textContent = config.version || '1.0.2';
            });
            
            const descEl = document.getElementById('app-description');
            if (descEl) descEl.textContent = config.description;
            
            const sizeEl = document.getElementById('app-size');
            if (sizeEl) sizeEl.textContent = config.file_size;

            if (config.placements) {
                const heroImg = document.getElementById('hero-img');
                if (heroImg && config.placements.hero) {
                    heroImg.src = config.placements.hero;
                }
                
                const downloadSection = document.getElementById('download');
                if (downloadSection && config.placements.download) {
                    downloadSection.style.backgroundImage = `linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.85)), url(${config.placements.download})`;
                    downloadSection.style.backgroundSize = 'cover';
                    downloadSection.style.backgroundPosition = 'center';
                }
            }

            const whyUsContainer = document.getElementById('why-us-container');
            if (whyUsContainer && config.why_us) {
                whyUsContainer.innerHTML = config.why_us.map(item => `
                    <div class="feature-card reveal-up">
                        <i class="${item.icon}"></i>
                        <h3>${item.title}</h3>
                        <p>${item.desc}</p>
                    </div>
                `).join('');
            }

            const screenshotsContainer = document.getElementById('screenshots-container');
            if (screenshotsContainer && config.screenshots) {
                screenshotsContainer.innerHTML = config.screenshots.map(s => {
                    if (!s.url) return '';
                    return `
                        <div class="screenshot-item reveal-up">
                            <img src="${s.url}" alt="${s.title || 'Screenshot'}" onerror="this.parentElement.style.display='none'">
                        </div>
                    `;
                }).join('');
            }
        } catch (err) {
            console.error('Error populating content:', err);
        }
    };

    const initBgCanvas = () => {
        const canvas = document.getElementById('bg-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        let width, height, particles = [];
        const resize = () => {
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
        };
        class Particle {
            constructor() {
                this.x = Math.random() * width;
                this.y = Math.random() * height;
                this.size = Math.random() * 2;
                this.speedX = (Math.random() - 0.5) * 0.5;
                this.speedY = (Math.random() - 0.5) * 0.5;
                this.color = Math.random() > 0.5 ? '#00f2ff' : '#7000ff';
            }
            update() {
                this.x += this.speedX;
                this.y += this.speedY;
                if (this.x > width) this.x = 0;
                if (this.x < 0) this.x = width;
                if (this.y > height) this.y = 0;
                if (this.y < 0) this.y = height;
            }
            draw() {
                ctx.fillStyle = this.color;
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fill();
            }
        }
        const initParticles = () => {
            particles = [];
            for (let i = 0; i < 100; i++) particles.push(new Particle());
        };
        const animate = () => {
            ctx.clearRect(0, 0, width, height);
            particles.forEach(p => {
                p.update();
                p.draw();
            });
            requestAnimationFrame(animate);
        };
        window.addEventListener('resize', resize);
        resize();
        initParticles();
        animate();
    };

    const initSoundEffects = () => {
        const playSound = (freq = 440, type = 'sine', duration = 0.1) => {
            try {
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = type;
                osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
                gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + duration);
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.start();
                osc.stop(audioCtx.currentTime + duration);
            } catch (e) {}
        };
        document.querySelectorAll('.btn, .nav-links a, .logo').forEach(el => {
            el.addEventListener('mouseenter', () => playSound(880, 'square', 0.05));
            el.addEventListener('click', () => playSound(440, 'triangle', 0.2));
        });
    };

    const setupEventListeners = () => {
        const menuToggle = document.getElementById('mobile-menu');
        const navLinks = document.querySelector('.nav-links');
        if (menuToggle && navLinks) {
            menuToggle.addEventListener('click', () => {
                navLinks.style.display = navLinks.style.display === 'flex' ? 'none' : 'flex';
                navLinks.style.flexDirection = 'column';
                navLinks.style.position = 'absolute';
                navLinks.style.top = '80px';
                navLinks.style.left = '0';
                navLinks.style.width = '100%';
                navLinks.style.background = 'rgba(0,0,0,0.9)';
                navLinks.style.padding = '20px';
            });
        }

        window.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey && (e.key === 'A' || e.key === 'a' || e.key === 'ф' || e.key === 'Ф')) {
                e.preventDefault();
                window.location.href = 'admin.html';
            }
        });

        const dlBtn = document.getElementById('download-btn');
        if (dlBtn) {
            dlBtn.addEventListener('click', () => {
                const container = document.getElementById('download-progress-container');
                const fill = document.getElementById('download-progress-fill');
                const status = document.getElementById('download-status');
                if (container && fill && status) {
                    dlBtn.style.display = 'none';
                    container.style.display = 'block';
                    let progress = 0;
                    const interval = setInterval(() => {
                        progress += Math.random() * 8;
                        if (progress >= 100) {
                            progress = 100;
                            clearInterval(interval);
                            status.textContent = 'ГОТОВО! НАЧИНАЕМ ЗАГРУЗКУ...';
                            const ts = new Date().getTime();
                            const baseUrl = (config && config.download_url) ? config.download_url : '#';
                            const downloadUrl = baseUrl.includes('?') ? `${baseUrl}&v=${ts}` : `${baseUrl}?v=${ts}`;
                            const link = document.createElement('a');
                            link.href = downloadUrl;
                            link.download = 'MoneyTracker.exe';
                            document.body.appendChild(link);
                            link.click();
                            document.body.removeChild(link);
                            setTimeout(() => {
                                container.style.display = 'none';
                                dlBtn.style.display = 'inline-flex';
                                status.textContent = 'ПОДГОТОВКА...';
                                fill.style.width = '0%';
                                alert('СИСТЕМА: ЗАГРУЗКА ЗАВЕРШЕНА УСПЕШНО');
                            }, 2000);
                        }
                        fill.style.width = progress + '%';
                        status.textContent = `ЗАГРУЗКА ДАННЫХ: ${Math.round(progress)}%`;
                    }, 80);
                }
            });
        }
    };

    const revealOnScroll = () => {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('active');
                }
            });
        }, { threshold: 0.1 });
        document.querySelectorAll('.reveal-up').forEach(el => observer.observe(el));
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
