const todayEl = document.getElementById("today");
if (todayEl) {
  todayEl.textContent = new Date().toLocaleDateString("en-PH", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

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

const sidebarToggle = document.getElementById("sidebar-toggle");

if (sidebarToggle) {
  const applySidebar = (collapsed) => {
    document.body.classList.toggle("sidebar-collapsed", collapsed);
    sidebarToggle.setAttribute("aria-expanded", String(!collapsed));
    sidebarToggle.setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
  };

  applySidebar(document.body.classList.contains("sidebar-collapsed"));

  sidebarToggle.addEventListener("click", () => {
    const collapsed = !document.body.classList.contains("sidebar-collapsed");
    applySidebar(collapsed);
    try {
      localStorage.setItem("caterSidebar", collapsed ? "collapsed" : "expanded");
    } catch (e) {}
  });
}
