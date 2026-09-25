// Open Colab links in a new tab, so the docs page stays open behind the notebook.
// Notebook markdown cannot set a link target, so the docs site sets it here.
// The "Open in Colab" badge is served from this site, as some browsers and
// networks block images from colab.research.google.com.
const colabBadge = new URL("colab-badge.svg", document.currentScript.src).href;

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll('a[href^="https://colab.research.google.com/"]').forEach((a) => {
    a.target = "_blank";
    a.rel = "noopener";
  });
  document.querySelectorAll('img[src="https://colab.research.google.com/assets/colab-badge.svg"]').forEach((img) => {
    img.src = colabBadge;
  });
});
