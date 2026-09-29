// Naukri-style Campus Placement Portal Vanilla JavaScript

document.addEventListener("DOMContentLoaded", function () {
  // 1. Auto-dismiss flash messages after 4.5 seconds
  const flashAlerts = document.querySelectorAll(".alert-dismissible");
  flashAlerts.forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = "opacity 0.5s ease";
      alert.style.opacity = "0";
      setTimeout(function () {
        alert.remove();
      }, 500);
    }, 4500);
  });

  // 2. Registration password confirmation match verification
  const regForm = document.querySelector("#studentRegisterForm");
  if (regForm) {
    const passwordInput = document.querySelector("#password");
    const confirmInput = document.querySelector("#confirm_password");
    const feedbackElem = document.querySelector("#passwordMatchFeedback");

    function validatePasswordMatch() {
      if (!passwordInput || !confirmInput || !feedbackElem) return;
      const pass = passwordInput.value;
      const confirm = confirmInput.value;

      if (confirm.length === 0) {
        feedbackElem.textContent = "";
        confirmInput.classList.remove("is-invalid", "is-valid");
        return;
      }

      if (pass === confirm) {
        feedbackElem.textContent = "Passwords match";
        feedbackElem.className = "form-hint text-success";
        confirmInput.classList.remove("is-invalid");
        confirmInput.classList.add("is-valid");
      } else {
        feedbackElem.textContent = "Passwords do not match";
        feedbackElem.className = "form-hint text-danger";
        confirmInput.classList.remove("is-valid");
        confirmInput.classList.add("is-invalid");
      }
    }

    passwordInput.addEventListener("input", validatePasswordMatch);
    confirmInput.addEventListener("input", validatePasswordMatch);

    regForm.addEventListener("submit", function (e) {
      if (passwordInput.value !== confirmInput.value) {
        e.preventDefault();
        alert("Please ensure both passwords match before submitting.");
        confirmInput.focus();
      }
    });
  }

  // 3. Confirm-before-action for delete actions
  const deleteForms = document.querySelectorAll(".form-confirm-delete");
  deleteForms.forEach(function (form) {
    form.addEventListener("submit", function (e) {
      const entityName = form.getAttribute("data-entity-name") || "this item";
      const confirmed = window.confirm(
        `Are you sure you want to permanently delete "${entityName}"? This action cannot be undone.`
      );
      if (!confirmed) {
        e.preventDefault();
      }
    });
  });
});
