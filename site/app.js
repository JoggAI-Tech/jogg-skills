const header = document.querySelector("[data-header]");
const menuToggle = document.querySelector(".menu-toggle");
const nav = document.querySelector("#site-nav");
const heroVideo = document.querySelector("[data-auto-video]");
const videoToggle = document.querySelector("[data-video-toggle]");
const videoToggleLabel = document.querySelector("[data-video-toggle-label]");
const copyButton = document.querySelector("[data-copy-command]");
const copyStatus = document.querySelector("#copy-status");
const installCommand = document.querySelector("#install-command");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function setHeaderState() {
  header?.classList.toggle("is-scrolled", window.scrollY > 24);
}

function closeMenu() {
  header?.classList.remove("is-menu-open");
  menuToggle?.setAttribute("aria-expanded", "false");
  menuToggle?.setAttribute("aria-label", "Open navigation");
}

function setVideoToggleState(isPaused) {
  videoToggle?.classList.toggle("is-paused", isPaused);
  videoToggle?.setAttribute("aria-label", isPaused ? "Play background video" : "Pause background video");
  if (videoToggleLabel) videoToggleLabel.textContent = isPaused ? "Play reel" : "Pause reel";
}

menuToggle?.addEventListener("click", () => {
  const willOpen = !header.classList.contains("is-menu-open");
  header.classList.toggle("is-menu-open", willOpen);
  menuToggle.setAttribute("aria-expanded", String(willOpen));
  menuToggle.setAttribute("aria-label", willOpen ? "Close navigation" : "Open navigation");
});

nav?.addEventListener("click", (event) => {
  if (event.target.closest("a")) closeMenu();
});

if (heroVideo && reduceMotion) {
  heroVideo.pause();
  setVideoToggleState(true);
}

videoToggle?.addEventListener("click", async () => {
  if (!heroVideo) return;

  if (heroVideo.paused) {
    try {
      await heroVideo.play();
      setVideoToggleState(false);
    } catch {
      setVideoToggleState(true);
    }
  } else {
    heroVideo.pause();
    setVideoToggleState(true);
  }
});

copyButton?.addEventListener("click", async () => {
  const command = installCommand.textContent.trim();

  try {
    await Promise.race([
      navigator.clipboard.writeText(command),
      new Promise((_, reject) => window.setTimeout(() => reject(new Error("Clipboard timeout")), 800)),
    ]);
    copyButton.textContent = "Copied";
    copyStatus.textContent = "Install command copied to clipboard.";
  } catch {
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(installCommand);
    selection.removeAllRanges();
    selection.addRange(range);
    copyButton.textContent = "Selected";
    copyStatus.textContent = "The install command is selected and ready to copy.";
  }

  window.setTimeout(() => {
    copyButton.textContent = "Copy";
    copyStatus.textContent = "";
  }, 2600);
});

document.querySelectorAll("[data-year]").forEach((node) => {
  node.textContent = new Date().getFullYear();
});

setHeaderState();
window.addEventListener("scroll", setHeaderState, { passive: true });
window.addEventListener("resize", () => {
  if (window.innerWidth > 900) closeMenu();
});

const revealNodes = [...document.querySelectorAll(".reveal")];

if (reduceMotion || !("IntersectionObserver" in window)) {
  revealNodes.forEach((node) => node.classList.add("is-visible"));
} else {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.12 }
  );

  revealNodes.forEach((node) => observer.observe(node));
}
