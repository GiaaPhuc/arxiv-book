/**
 * Collapsible Table of Contents for Jupyter Book / Sphinx Book Theme
 * Enhances Milestone sections (captions) with toggle collapse/expand and persistent state.
 */
document.addEventListener("DOMContentLoaded", function () {
  const captions = document.querySelectorAll(".bd-sidebar-primary .bd-links p.caption");

  captions.forEach(function (caption, index) {
    const nextList = caption.nextElementSibling;
    if (!nextList || !nextList.classList.contains("bd-sidenav")) {
      return;
    }

    // Mark as interactive collapsible header
    caption.classList.add("collapsible-caption");
    caption.setAttribute("role", "button");
    caption.setAttribute("tabindex", "0");

    // Add toggle chevron icon
    const toggleIcon = document.createElement("span");
    toggleIcon.className = "caption-toggle-icon";
    toggleIcon.setAttribute("aria-hidden", "true");
    toggleIcon.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>`;
    caption.appendChild(toggleIcon);

    // Identify if the current active page is inside this section
    const hasActiveChild = nextList.querySelector(".current, .active") !== null;
    const storageKey = "jb_toc_caption_" + (caption.textContent || "").trim().slice(0, 20);

    // Default: Milestone 1 stays open if active or by default; Milestone 2 can be closed if stored
    let isCollapsed = false;
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored !== null) {
        isCollapsed = stored === "true";
      }
    } catch (e) {
      // localStorage may be unavailable
    }

    // Always keep section open if currently viewing a page inside it
    if (hasActiveChild) {
      isCollapsed = false;
    }

    function updateState(collapsed) {
      if (collapsed) {
        caption.classList.add("is-collapsed");
        nextList.classList.add("is-collapsed");
        caption.setAttribute("aria-expanded", "false");
      } else {
        caption.classList.remove("is-collapsed");
        nextList.classList.remove("is-collapsed");
        caption.setAttribute("aria-expanded", "true");
      }
      try {
        localStorage.setItem(storageKey, collapsed ? "true" : "false");
      } catch (e) {}
    }

    updateState(isCollapsed);

    // Toggle on click
    caption.addEventListener("click", function (e) {
      e.preventDefault();
      const nowCollapsed = !caption.classList.contains("is-collapsed");
      updateState(nowCollapsed);
    });

    // Toggle on Enter or Space
    caption.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        const nowCollapsed = !caption.classList.contains("is-collapsed");
        updateState(nowCollapsed);
      }
    });
  });
});
