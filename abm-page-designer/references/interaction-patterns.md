# Interaction Patterns Reference

Concrete implementation patterns for Awwwards-level interactions in a single self-contained HTML file. All patterns use native CSS + vanilla JS only.

## Scroll Reveal Engine

```javascript
const reveals = document.querySelectorAll('[data-reveal]');
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const el = entry.target;
      const delay = el.dataset.revealDelay || 0;
      setTimeout(() => el.classList.add('revealed'), delay);
      observer.unobserve(el);
    }
  });
}, { threshold: 0.15, rootMargin: '0px 0px -60px 0px' });
reveals.forEach(el => observer.observe(el));
```

```css
[data-reveal] {
  opacity: 0;
  transform: translateY(24px);
  transition: opacity 0.7s cubic-bezier(0.16, 1, 0.3, 1),
              transform 0.7s cubic-bezier(0.16, 1, 0.3, 1);
}
[data-reveal].revealed {
  opacity: 1;
  transform: translateY(0);
}
[data-reveal="scale"] {
  transform: scale(0.92);
}
[data-reveal="scale"].revealed {
  transform: scale(1);
}
[data-reveal="clip"] {
  clip-path: inset(100% 0 0 0);
  transform: none;
}
[data-reveal="clip"].revealed {
  clip-path: inset(0 0 0 0);
  transition: clip-path 0.9s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.6s ease;
}
```

### Stagger Children

```javascript
document.querySelectorAll('[data-stagger]').forEach(parent => {
  const children = parent.querySelectorAll('[data-reveal]');
  children.forEach((child, i) => {
    child.dataset.revealDelay = i * 100;
  });
});
```

## Parallax Engine

```javascript
let ticking = false;
function updateParallax() {
  const scrollY = window.scrollY;
  document.querySelectorAll('[data-parallax]').forEach(el => {
    const speed = parseFloat(el.dataset.parallax) || 0.3;
    const rect = el.getBoundingClientRect();
    const center = rect.top + rect.height / 2;
    const offset = (center - window.innerHeight / 2) * speed;
    el.style.transform = `translate3d(0, ${offset}px, 0)`;
  });
  ticking = false;
}
window.addEventListener('scroll', () => {
  if (!ticking) {
    requestAnimationFrame(updateParallax);
    ticking = true;
  }
}, { passive: true });
```

## Magnetic Buttons

```javascript
document.querySelectorAll('[data-magnetic]').forEach(btn => {
  btn.addEventListener('mousemove', (e) => {
    const rect = btn.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;
    const strength = parseFloat(btn.dataset.magnetic) || 0.3;
    btn.style.transform = `translate(${x * strength}px, ${y * strength}px)`;
  });
  btn.addEventListener('mouseleave', () => {
    btn.style.transform = 'translate(0, 0)';
    btn.style.transition = 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
  });
  btn.addEventListener('mouseenter', () => {
    btn.style.transition = 'transform 0.15s ease-out';
  });
});
```

## Number Count-Up

```javascript
function countUp(el) {
  const target = parseFloat(el.dataset.count);
  const prefix = el.dataset.countPrefix || '';
  const suffix = el.dataset.countSuffix || '';
  const decimals = (el.dataset.countDecimals || 0) | 0;
  const duration = 1400;
  const start = performance.now();

  function step(now) {
    const t = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - t, 4); // easeOutQuart
    const current = target * eased;
    el.textContent = prefix + current.toLocaleString('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }) + suffix;
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// Trigger on scroll
const countObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      countUp(entry.target);
      countObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.5 });
document.querySelectorAll('[data-count]').forEach(el => countObserver.observe(el));
```

## Hero Loading Choreography

```css
@keyframes heroFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes heroSlideUp {
  from { opacity: 0; transform: translateY(32px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes heroScaleIn {
  from { opacity: 0; transform: scale(0.9); }
  to { opacity: 1; transform: scale(1); }
}
@keyframes heroPulse {
  0%, 100% { opacity: 0.4; transform: translateY(0); }
  50% { opacity: 1; transform: translateY(6px); }
}

.hero-bg { animation: heroFadeIn 0.8s ease-out both; }
.hero-logo { animation: heroSlideUp 0.6s cubic-bezier(0.16,1,0.3,1) 0.3s both; }
.hero-headline { animation: heroSlideUp 0.7s cubic-bezier(0.16,1,0.3,1) 0.5s both; }
.hero-sub { animation: heroSlideUp 0.6s cubic-bezier(0.16,1,0.3,1) 0.8s both; }
.hero-cta { animation: heroScaleIn 0.5s cubic-bezier(0.34,1.56,0.64,1) 1.1s both; }
.hero-scroll-indicator { animation: heroPulse 2s ease-in-out 2s infinite; opacity: 0; animation-fill-mode: forwards; }
```

## Split Text Reveal

```javascript
function splitReveal(el) {
  const text = el.textContent;
  const words = text.split(' ');
  el.innerHTML = words.map((word, i) =>
    `<span style="display:inline-block;overflow:hidden;">
      <span style="display:inline-block;transform:translateY(110%);transition:transform 0.6s cubic-bezier(0.16,1,0.3,1) ${i * 0.08}s">${word}</span>
    </span>`
  ).join(' ');

  requestAnimationFrame(() => {
    el.querySelectorAll('span > span').forEach(s => {
      s.style.transform = 'translateY(0)';
    });
  });
}
```

## Smooth Scroll With Header Offset

```javascript
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', (e) => {
    e.preventDefault();
    const target = document.querySelector(anchor.getAttribute('href'));
    if (!target) return;
    const headerH = document.querySelector('nav, header')?.offsetHeight || 0;
    const top = target.getBoundingClientRect().top + window.scrollY - headerH - 24;
    window.scrollTo({ top, behavior: 'smooth' });

    if (typeof flzAnalytic === 'function') {
      flzAnalytic('nav_click', { text: anchor.innerText.trim(), area: 'navigation' });
    }
  });
});
```

## Modal System

```javascript
function openModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
  modal.querySelector('[data-close]')?.focus();
  if (typeof flzAnalytic === 'function') {
    flzAnalytic('modal_open', { text: modal.dataset.title || id, area: 'modal' });
  }
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.remove('active');
  document.body.style.overflow = '';
  if (typeof flzAnalytic === 'function') {
    flzAnalytic('modal_close', { text: modal.dataset.title || id, area: 'modal' });
  }
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelector('.modal.active')?.id &&
      closeModal(document.querySelector('.modal.active').id);
  }
});
```

```css
.modal {
  position: fixed; inset: 0; z-index: 1000;
  display: flex; align-items: center; justify-content: center;
  opacity: 0; pointer-events: none;
  transition: opacity 0.3s ease;
}
.modal.active {
  opacity: 1; pointer-events: auto;
}
.modal-overlay {
  position: absolute; inset: 0;
  background: rgba(0,0,0,0.5);
  backdrop-filter: blur(8px);
}
.modal-content {
  position: relative; z-index: 1;
  max-width: 640px; width: 90%;
  max-height: 85vh; overflow-y: auto;
  transform: translateY(16px) scale(0.97);
  transition: transform 0.35s cubic-bezier(0.16,1,0.3,1);
}
.modal.active .modal-content {
  transform: translateY(0) scale(1);
}
```

## Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  [data-reveal] { opacity: 1; transform: none; clip-path: none; }
  [data-parallax] { transform: none !important; }
}
```

## Card Hover Lift

```css
.card {
  transition: transform 0.35s cubic-bezier(0.16,1,0.3,1),
              box-shadow 0.35s cubic-bezier(0.16,1,0.3,1);
}
.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(var(--shadow-color), 0.12);
}
```

## Grain Texture Overlay

```css
.grain::after {
  content: '';
  position: absolute; inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
  pointer-events: none;
  z-index: 1;
}
```
