(function() {
    'use strict';

    let config = null; // Global within IIFE

    // 1. Initial State & Elements
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
                initFullscreenViewer(); // Initialize viewer after preloader
            }, 800);
        }
    };

    // 2. Fullscreen Viewer
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

        // Attach to all images on click
        document.body.addEventListener('click', (e) => {
            if (e.target.tagName === 'IMG' && (e.target.closest('.screenshot-item') || e.target.closest('.media-item') || e.target.id === 'hero-img')) {
                openViewer(e.target.src);
            }
        });

        close.addEventListener('click', closeViewer);
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeViewer();
        });
        window.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeViewer();
        });
    };

    // 2. Load config.json with Timeout
    const loadConfig = async () => {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 sec timeout

        try {
            if (window.location.protocol === 'file:') {
                return getFallbackConfig();
            }
            
            const response = await fetch('/config.json', { signal: controller.signal });
            clearTimeout(timeoutId);
            
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            console.warn('Config fetch failed or timed out, using fallback:', error.name === 'AbortError' ? 'Timeout' : error.message);
            return getFallbackConfig();
        }
    };

    const getFallbackConfig = () => {
        return {
            "app_name": "MoneyTracker Pro",
            "version": "1.0.0",
            "file_size": "45.2 MB",
            "description": "Профессиональное решение для автоматизации учета финансов, управления активами и контроля времени на базе Ledger-архитектуры.",
            "why_us": [
                { "icon": "fas fa-microchip", "title": "Ledger Core", "desc": "100% точность баланса благодаря архитектуре двойной записи." },
                { "icon": "fas fa-bolt", "title": "Speed", "desc": "Мгновенная работа интерфейса на базе асинхронного SQLite движка." },
                { "icon": "fas fa-shield-alt", "title": "Security", "desc": "Локальное хранение данных с AES-256 шифрованием." }
            ],
            "features": [
                {
                    "category": "Учет и Аналитика",
                    "items": [
                        { "icon": "fas fa-chart-line", "title": "Net Worth", "desc": "Автоматический расчет чистого капитала в реальном времени." },
                        { "icon": "fas fa-puzzle-piece", "title": "Плагины", "desc": "Расширение функционала через модульную систему." }
                    ]
                }
            ],
            "screenshots": [
                { "url": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=800&q=80", "title": "Dashboard" },
                { "url": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=800&q=80", "title": "Analytics" }
            ],
            "contacts": {
                "discord": "discord.gg/moneytracker",
                "telegram": "@moneytracker_pro",
                "email": "support@moneytracker.pro"
            }
        };
    };

    // 3. Populate Content
    const populateContent = (config) => {
        try {
            document.querySelectorAll('.app-version').forEach(el => {
                el.textContent = config.version || '1.0.0';
            });
            
            const descEl = document.getElementById('app-description');
            if (descEl) descEl.textContent = config.description;
            
            const sizeEl = document.getElementById('app-size');
            if (sizeEl) sizeEl.textContent = config.file_size;

            // Apply Dynamic Placements
            const ts = new Date().getTime(); // Cache buster
            if (config.placements) {
                const heroImg = document.getElementById('hero-img');
                if (heroImg && config.placements.hero) {
                    heroImg.src = config.placements.hero.startsWith('/') ? `${config.placements.hero}?v=${ts}` : config.placements.hero;
                    heroImg.onerror = () => {
                        console.warn('Hero image failed to load, using default');
                        heroImg.src = 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1200&q=80';
                    };
                }
                
                const downloadSection = document.getElementById('download');
                if (downloadSection && config.placements.download) {
                    const dlUrl = config.placements.download.startsWith('/') ? `${config.placements.download}?v=${ts}` : config.placements.download;
                    downloadSection.style.backgroundImage = `linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.85)), url(${dlUrl})`;
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

            const featuresContainer = document.getElementById('features-container');
            if (featuresContainer && config.features) {
                featuresContainer.innerHTML = config.features.map(cat => `
                    <div class="feature-category" style="grid-column: 1/-1; margin-top: 40px;">
                        <h3>${cat.category}</h3>
                    </div>
                    ${cat.items.map(f => `
                        <div class="feature-card reveal-up">
                            <i class="${f.icon}"></i>
                            <h3>${f.title}</h3>
                            <p>${f.desc}</p>
                        </div>
                    `).join('')}
                `).join('');
            }

            const screenshotsContainer = document.getElementById('screenshots-container');
            if (screenshotsContainer && config.screenshots) {
                screenshotsContainer.innerHTML = config.screenshots.map(s => {
                    if (!s.url) return '';
                    const url = s.url.startsWith('/') ? `${s.url}?v=${ts}` : s.url;
                    return `
                        <div class="screenshot-item reveal-up">
                            <img src="${url}" alt="${s.title || 'Screenshot'}" onerror="this.parentElement.style.display='none'">
                        </div>
                    `;
                }).join('');
            }

            const discordEl = document.getElementById('contact-discord');
            if (discordEl && config.contacts) discordEl.textContent = config.contacts.discord;
            
            const telegramEl = document.getElementById('contact-telegram');
            if (telegramEl && config.contacts) telegramEl.textContent = config.contacts.telegram;
            
            const emailEl = document.getElementById('contact-email');
            if (emailEl && config.contacts) emailEl.textContent = config.contacts.email;
        } catch (err) {
            console.error('Error populating content:', err);
        }
    };

    // 4. Background Canvas (Matrix/Cyber Effect)
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

    // 5. Sound Effects (Simple Beeps)
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

    // 6. Events
    const setupEventListeners = () => {
        // Mobile Menu
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

        // Admin Login Shortcut: Ctrl + Shift + A
        window.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey && (e.key === 'A' || e.key === 'a' || e.key === 'ф' || e.key === 'Ф')) {
                e.preventDefault();
                window.location.href = 'admin.html';
            }
        });

        // Admin Modal (Keep for compatibility if triggers exist)
        const openModal = () => window.location.href = 'admin.html';
        const closeModal = () => {
            const modal = document.getElementById('admin-modal');
            if (modal) modal.style.display = 'none';
        };
        
        const logoTrigger = document.getElementById('logo-admin-trigger');
        if (logoTrigger) logoTrigger.addEventListener('click', openModal);
        
        const footerTrigger = document.getElementById('footer-admin-trigger');
        if (footerTrigger) footerTrigger.addEventListener('click', openModal);
        
        const closeBtn = document.getElementById('close-admin');
        if (closeBtn) closeBtn.addEventListener('click', closeModal);

        // Download Logic
        const dlBtn = document.getElementById('download-btn');
        if (dlBtn) {
            // Apply text from config
            if (config && config.download_text) {
                dlBtn.innerHTML = `<span>${config.download_text}</span>`;
            }

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
                            
                            // Trigger actual file download with cache buster
                            const ts = new Date().getTime();
                            const baseUrl = (config && config.download_url) ? config.download_url : '#';
                            const downloadUrl = baseUrl.includes('?') ? `${baseUrl}&v=${ts}` : `${baseUrl}?v=${ts}`;
                            
                            const link = document.createElement('a');
                            link.href = downloadUrl;
                            // Ensure the original filename is used for the download
                            const filename = baseUrl.split('/').pop().split('?')[0] || 'MoneyTracker.exe';
                            link.download = filename;
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

        // Admin Login (Legacy - if still used)
        const adminLoginBtn = document.getElementById('admin-login-btn');
        if (adminLoginBtn) {
            adminLoginBtn.addEventListener('click', () => {
                const user = document.getElementById('admin-user').value;
                const pass = document.getElementById('admin-pass').value;
                if (user === 'admin' && pass === 'admin123') {
                    localStorage.setItem('admin_logged_in', 'true');
                    window.location.href = 'dashboard.html';
                } else {
                    const err = document.getElementById('admin-login-error');
                    if (err) {
                        err.textContent = 'ДОСТУП ЗАПРЕЩЕН: НЕВЕРНЫЙ КОД';
                        err.style.display = 'block';
                    }
                }
            });
        }
    };

    // 7. Reveal Animation
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

    document.addEventListener('DOMContentLoaded', init);
})();
