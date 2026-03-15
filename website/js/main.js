(function() {
    'use strict';

    // 1. Initial State & Elements
    const init = async () => {
        const config = await loadConfig();
        if (config) {
            populateContent(config);
            initBgCanvas();
            initSoundEffects();
        }
        setupEventListeners();
        revealOnScroll();
    };

    // 2. Load config.json
    const loadConfig = async () => {
        try {
            if (window.location.protocol === 'file:') {
                return getFallbackConfig();
            }
            const response = await fetch('config.json');
            return await response.json();
        } catch (error) {
            console.error('Error loading config, using fallback:', error);
            return getFallbackConfig();
        }
    };

    const getFallbackConfig = () => {
        return {
            "app_name": "MoneyTracker Pro",
            "version": "9.3.0",
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
        document.querySelectorAll('.app-version').forEach(el => el.textContent = config.version);
        document.getElementById('app-description').textContent = config.description;
        document.getElementById('app-size').textContent = config.file_size;

        const whyUsContainer = document.getElementById('why-us-container');
        if (whyUsContainer) {
            whyUsContainer.innerHTML = config.why_us.map(item => `
                <div class="feature-card reveal-up">
                    <i class="${item.icon}"></i>
                    <h3>${item.title}</h3>
                    <p>${item.desc}</p>
                </div>
            `).join('');
        }

        const featuresContainer = document.getElementById('features-container');
        if (featuresContainer) {
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
        if (screenshotsContainer) {
            screenshotsContainer.innerHTML = config.screenshots.map(s => `
                <div class="screenshot-item reveal-up">
                    <img src="${s.url}" alt="${s.title}">
                </div>
            `).join('');
        }

        document.getElementById('contact-discord').textContent = config.contacts.discord;
        document.getElementById('contact-telegram').textContent = config.contacts.telegram;
        document.getElementById('contact-email').textContent = config.contacts.email;
    };

    // 4. Background Canvas (Matrix/Cyber Effect)
    const initBgCanvas = () => {
        const canvas = document.getElementById('bg-canvas');
        const ctx = canvas.getContext('2d');
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
        if (menuToggle) {
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
        const closeModal = () => document.getElementById('admin-modal').style.display = 'none';
        
        document.getElementById('logo-admin-trigger').addEventListener('click', openModal);
        document.getElementById('footer-admin-trigger').addEventListener('click', openModal);
        document.getElementById('close-admin').addEventListener('click', closeModal);

        // Download Logic
        const dlBtn = document.getElementById('download-btn');
        if (dlBtn) {
            dlBtn.addEventListener('click', () => {
                dlBtn.style.display = 'none';
                const container = document.getElementById('download-progress-container');
                const fill = document.getElementById('download-progress-fill');
                const status = document.getElementById('download-status');
                container.style.display = 'block';
                
                let progress = 0;
                const interval = setInterval(() => {
                    progress += Math.random() * 5;
                    if (progress >= 100) {
                        progress = 100;
                        clearInterval(interval);
                        status.textContent = 'ГОТОВО! ЗАГРУЗКА...';
                        setTimeout(() => window.location.href = '#', 1000);
                    }
                    fill.style.width = progress + '%';
                    status.textContent = `ЗАГРУЗКА ДАННЫХ: ${Math.round(progress)}%`;
                }, 100);
            });
        }

        // Admin Login
        document.getElementById('admin-login-btn').addEventListener('click', () => {
            const user = document.getElementById('admin-user').value;
            const pass = document.getElementById('admin-pass').value;
            if (user === 'admin' && pass === 'admin123') {
                localStorage.setItem('admin_logged_in', 'true');
                window.location.href = 'dashboard.html';
            } else {
                const err = document.getElementById('admin-login-error');
                err.textContent = 'ДОСТУП ЗАПРЕЩЕН: НЕВЕРНЫЙ КОД';
                err.style.display = 'block';
            }
        });
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
