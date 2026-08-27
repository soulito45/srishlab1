// ==========================================================================
// main.js - shared front-end logic for IDAA
// ==========================================================================

(function () {
  const root = document.documentElement;
  const toggleBtn = document.getElementById("themeToggle");
  const storedTheme = localStorage.getItem("idaa-theme") || "dark";
  root.setAttribute("data-theme", storedTheme);
  updateIcon(storedTheme);

  if (toggleBtn) {
    toggleBtn.addEventListener("click", function () {
      const current = root.getAttribute("data-theme");
      const next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      localStorage.setItem("idaa-theme", next);
      updateIcon(next);
    });
  }

  function updateIcon(theme) {
    if (!toggleBtn) return;
    toggleBtn.innerHTML = theme === "dark"
      ? '<i class="bi bi-moon-stars-fill"></i>'
      : '<i class="bi bi-sun-fill"></i>';
  }

  // Auto-dismiss flash messages after 5s
  document.querySelectorAll(".idaa-alert").forEach(function (alertEl) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alertEl);
      bsAlert.close();
    }, 5000);
  });

  // File input UX: show chosen filename
  const fileInput = document.getElementById("fileInput");
  const fileLabel = document.getElementById("fileLabel");
  if (fileInput && fileLabel) {
    function showSelectedFile() {
      if (!fileInput.files.length) return;
      fileLabel.textContent = fileInput.files[0].name;
      const icon = document.createElement("i");
      icon.className = "bi bi-file-earmark-check-fill me-2";
      icon.setAttribute("aria-hidden", "true");
      fileLabel.prepend(icon);
    }

    fileInput.addEventListener("change", function () {
      showSelectedFile();
    });
    fileLabel.addEventListener("dragover", function (event) {
      event.preventDefault();
      fileLabel.classList.add("is-dragging");
    });
    fileLabel.addEventListener("dragleave", function () {
      fileLabel.classList.remove("is-dragging");
    });
    fileLabel.addEventListener("drop", function (event) {
      event.preventDefault();
      fileLabel.classList.remove("is-dragging");
      if (event.dataTransfer.files.length) {
        fileInput.files = event.dataTransfer.files;
        showSelectedFile();
      }
    });
  }

  // Keep users informed while the server parses and analyzes an upload.
  const uploadForm = document.getElementById("uploadForm");
  const uploadSubmit = document.getElementById("uploadSubmit");
  const analysisLoading = document.getElementById("analysisLoading");
  if (uploadForm && uploadSubmit && analysisLoading) {
    uploadForm.addEventListener("submit", function (event) {
      if (!uploadForm.checkValidity()) return;
      event.preventDefault();
      uploadSubmit.disabled = true;
      uploadForm.hidden = true;
      analysisLoading.hidden = false;

      const steps = analysisLoading.querySelectorAll(".analysis-step");
      const analysisStatus = document.getElementById("analysisStatus");
      const statusMessages = [
        "Opening the file and mapping its columns.",
        "Normalizing values, types, blanks, and duplicate rows.",
        "Preparing profiles, charts, and quality signals.",
        "Almost there. Finalizing your analysis workspace."
      ];
      steps.forEach(function (step, index) {
        setTimeout(function () {
          steps.forEach(function (item) { item.classList.remove("is-active"); });
          step.classList.add("is-active");
          if (analysisStatus) analysisStatus.textContent = statusMessages[index + 1] || statusMessages[3];
        }, (index + 1) * 850);
      });

      setTimeout(function () { uploadForm.submit(); }, 3200);
    });
  }
})();

// Common Plotly render helper
function renderPlot(divId, figJson) {
  if (!figJson || figJson.error) return;
  const el = document.getElementById(divId);
  if (!el) return;
  Plotly.newPlot(el, figJson.data, figJson.layout, { responsive: true, displaylogo: false });
}
