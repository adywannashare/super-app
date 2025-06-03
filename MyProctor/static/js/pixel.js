// pixel.js

// NAVBAR SHRINK ON SCROLL
window.onscroll = function () {
    const nav = document.querySelector('.navbar');
    if (window.pageYOffset > 100) {
        nav.classList.add('navbar-shrink');
    } else {
        nav.classList.remove('navbar-shrink');
    }
};

// SMOOTH SCROLLING TO ANCHORS
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});

// TOOLTIP INIT (if Bootstrap tooltips used)
$(function () {
    $('[data-toggle="tooltip"]').tooltip();
});

// Scroll-triggered animations (requires Onscreen.js or similar)
document.addEventListener('DOMContentLoaded', () => {
    const items = document.querySelectorAll('.animate-on-scroll');
    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animated');
                observer.unobserve(entry.target);
            }
        });
    });

    items.forEach(item => {
        observer.observe(item);
    });
});
  