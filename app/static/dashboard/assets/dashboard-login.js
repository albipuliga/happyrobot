const form = document.getElementById("dashboard-login-form");
const passwordInput = document.getElementById("password");
const submitButton = document.getElementById("submit-button");
const errorMessage = document.getElementById("error-message");

passwordInput.focus();

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitButton.disabled = true;
  errorMessage.textContent = "";

  try {
    const response = await fetch("/dashboard/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ password: passwordInput.value }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: "Invalid password." }));
      throw new Error(payload.detail || "Invalid password.");
    }

    window.location.reload();
  } catch (error) {
    errorMessage.textContent = error.message || "Invalid password.";
    passwordInput.select();
  } finally {
    submitButton.disabled = false;
  }
});
