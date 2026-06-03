document.addEventListener("DOMContentLoaded", () => {
    const messages = [
        "Live operations view is ready.",
        "Department updates are organized in one place.",
        "Reports and activity stay visible to managers.",
        "Teams can move faster with clearer communication."
    ];

    const messageTarget = document.getElementById("dynamic-message");
    let messageIndex = 0;

    if (messageTarget) {
        setInterval(() => {
            messageIndex = (messageIndex + 1) % messages.length;
            messageTarget.style.opacity = "0";

            setTimeout(() => {
                messageTarget.textContent = messages[messageIndex];
                messageTarget.style.opacity = "1";
            }, 220);
        }, 3200);
    }

    // Scroll-reveal effect for elements with .animate-in
    const revealElements = document.querySelectorAll(".animate-in");
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add("visible");
                // Stop observing after the animation has triggered
                revealObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    revealElements.forEach((el) => revealObserver.observe(el));

    const counters = document.querySelectorAll("[data-count]");

    const animateCounter = (counter) => {
        const target = Number(counter.dataset.count);
        const duration = 1200;
        const start = performance.now();

        const tick = (now) => {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            counter.textContent = Math.round(target * eased);

            if (progress < 1) {
                requestAnimationFrame(tick);
            }
        };

        requestAnimationFrame(tick);
    };

    if (counters.length) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.35 });

        counters.forEach((counter) => observer.observe(counter));
    }

    const clock = document.getElementById("office-clock");

    const updateClock = () => {
        if (!clock) {
            return;
        }

        clock.textContent = new Intl.DateTimeFormat([], {
            hour: "2-digit",
            minute: "2-digit"
        }).format(new Date());
    };

    updateClock();
    setInterval(updateClock, 30000);
});
