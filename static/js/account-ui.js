(function () {
  "use strict";

  document.querySelectorAll(".password-visibility-toggle").forEach(function (button) {
    button.addEventListener("click", function () {
      var wrap = button.closest(".password-input-wrap");
      var input = wrap && wrap.querySelector("input");
      if (!input) return;
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      button.textContent = show ? "Hide" : "Show";
      button.setAttribute("aria-label", show ? "Hide password" : "Show password");
      button.setAttribute("aria-pressed", show ? "true" : "false");
    });
  });

  document.querySelectorAll("[data-photo-preview]").forEach(function (preview) {
    var form = preview.closest("form");
    var input = form && form.querySelector('input[type="file"]');
    var fallback = form && form.querySelector("[data-photo-fallback]");
    var current = form && form.querySelector("[data-photo-current]");
    var status = form && form.querySelector("[data-photo-status]");
    var objectUrl = null;
    if (!input) return;

    input.addEventListener("change", function () {
      var file = input.files && input.files[0];
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
        objectUrl = null;
      }
      if (!file) {
        preview.hidden = true;
        preview.removeAttribute("src");
        if (current) current.hidden = false;
        if (fallback) fallback.hidden = false;
        if (status) status.textContent = "Photo selection cleared. Save your profile to keep the current photo.";
        return;
      }
      if (!/^image\/(jpeg|png|webp)$/.test(file.type) || file.size > 5 * 1024 * 1024) {
        input.setCustomValidity("Choose a JPG, PNG, or WebP image up to 5 MB.");
        input.reportValidity();
        input.value = "";
        return;
      }
      input.setCustomValidity("");

// Hide the saved/current photo immediately.
// This prevents the old and new photos from appearing together.
if (current) current.hidden = true;
if (fallback) fallback.hidden = true;

preview.hidden = true;
preview.removeAttribute("src");

objectUrl = URL.createObjectURL(file);
preview.onload = function () {
  preview.hidden = false;
};

preview.onerror = function () {
  preview.hidden = true;
  preview.removeAttribute("src");

  if (current) current.hidden = false;
  if (fallback) fallback.hidden = false;

  input.setCustomValidity("This image could not be previewed. Choose another file.");
  input.reportValidity();
  input.value = "";
};
preview.src = objectUrl;
      preview.onerror = function () {
        preview.hidden = true;
        input.setCustomValidity("This image could not be previewed. Choose another file.");
        input.reportValidity();
        input.value = "";
      };
      preview.src = objectUrl;
      if (status) status.textContent = file.name + " selected. Save your profile to apply it.";
    });

    form.addEventListener("submit", function () {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    });
  });

  document.querySelectorAll("form[data-submit-state]").forEach(function (form) {
    form.addEventListener("submit", function () {
      if (!form.checkValidity()) return;
      var button = form.querySelector('button[type="submit"],input[type="submit"]');
      if (!button) return;
      button.dataset.originalLabel = button.textContent;
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      button.textContent = form.dataset.submitState;
    });
  });

  document.addEventListener("click", function (event) {
    var openMenus = document.querySelectorAll(".account-menu[open]");
    openMenus.forEach(function (menu) {
      if (!menu.contains(event.target)) menu.open = false;
    });
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      document.querySelectorAll(".account-menu[open]").forEach(function (menu) {
        menu.open = false;
        menu.querySelector("summary").focus();
      });
    }
  });
})();
