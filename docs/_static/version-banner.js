// Reword the theme's version warning banner, which has no setting for its text.
// The theme fills the banner after fetching switcher.json, so watch for it.
document.addEventListener("DOMContentLoaded", () => {
  const banner = document.querySelector("#bd-header-version-warning");
  if (!banner) return;
  const reword = () => {
    banner.querySelectorAll("strong").forEach((bold) => {
      if (bold.textContent === "an unstable development version") {
        bold.textContent = "a version in ongoing development";
      }
    });
  };
  reword();
  new MutationObserver(reword).observe(banner, { childList: true, subtree: true });
});
