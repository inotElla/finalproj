// Show today's date in the dashboard top bar.
const todayEl = document.getElementById("today");
if (todayEl) {
  todayEl.textContent = new Date().toLocaleDateString("en-PH", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// Registration: tell the user right away if the two passwords differ.
const password = document.getElementById("password");
const confirmPassword = document.getElementById("confirm_password");

if (password && confirmPassword) {
  const checkMatch = () => {
    const mismatch = confirmPassword.value && password.value !== confirmPassword.value;
    confirmPassword.setCustomValidity(mismatch ? "Passwords must match." : "");
  };
  password.addEventListener("input", checkMatch);
  confirmPassword.addEventListener("input", checkMatch);
}
