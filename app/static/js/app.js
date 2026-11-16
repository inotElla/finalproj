// ---------- Today's date in the top bar ----------
const todayEl = document.getElementById("today");
if (todayEl) {
  todayEl.textContent = new Date().toLocaleDateString("en-PH", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// ---------- Password and confirm-password must match ----------
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

// ---------- Collapse / expand the sidebar ----------
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

// ---------- "Are you sure?" as a pop-up instead of the browser's confirm() ----------
// Several forms (Delete, Remove, Undo...) are written in the HTML as
//   onsubmit="return confirm('Delete this?');"
// Instead of editing every page, we read that message here, remove the old attribute,
// and ask with a Bootstrap modal. If Bootstrap is missing, the plain confirm() is used.
const confirmedForms = new WeakSet(); // forms the person has already said "yes" to
let confirmModalEl = null;

document.querySelectorAll("form[onsubmit*='confirm(']").forEach((form) => {
  const found = form.getAttribute("onsubmit").match(/confirm\((['"])(.*?)\1\)/);
  if (found) {
    form.dataset.confirm = found[2];
    form.removeAttribute("onsubmit");
  }
});

const askConfirm = (message, onYes) => {
  if (!window.bootstrap) {
    if (window.confirm(message)) onYes();
    return;
  }
  if (!confirmModalEl) {
    confirmModalEl = document.createElement("div");
    confirmModalEl.className = "modal fade";
    confirmModalEl.tabIndex = -1;
    confirmModalEl.setAttribute("aria-labelledby", "confirmTitle");
    confirmModalEl.setAttribute("aria-hidden", "true");
    confirmModalEl.innerHTML = `
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content" style="border-top:5px solid var(--bs-danger);">
          <div class="modal-header border-0 pb-0">
            <h2 class="modal-title h5" id="confirmTitle">Are you sure?</h2>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body"><p class="mb-0" id="confirmMessage"></p></div>
          <div class="modal-footer border-0 pt-0">
            <button type="button" class="btn btn-soft" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-danger" id="confirmYes">Yes, continue</button>
          </div>
        </div>
      </div>`;
    document.body.appendChild(confirmModalEl);
  }
  // textContent (not innerHTML) so the message can never be read as HTML.
  confirmModalEl.querySelector("#confirmMessage").textContent = message;

  const modal = bootstrap.Modal.getOrCreateInstance(confirmModalEl);
  const yes = confirmModalEl.querySelector("#confirmYes");
  const fresh = yes.cloneNode(true); // a new button, so old click handlers are dropped
  yes.replaceWith(fresh);
  fresh.addEventListener("click", () => {
    modal.hide();
    onYes();
  });
  confirmModalEl.addEventListener("shown.bs.modal", () => fresh.focus(), { once: true });
  modal.show();
};

// ---------- Client-side form validation (every form that saves something) ----------
// The server checks everything again, so this is only for speed and friendliness:
// the person sees what is wrong before anything is sent.
//
// How it works, for every <form method="POST">:
//   1. The browser's own checks (required, minlength, maxlength, min, max, type="email"...)
//      come from attributes that Flask-WTF already puts on the boxes.
//   2. On submit we check them ourselves, show the message under the box, and stop.
//   3. When the form is fine, the buttons are disabled so a double click cannot send it twice.
const postForms = document.querySelectorAll("form[method='POST'], form[method='post']");

const textBoxes = (form) =>
  form.querySelectorAll("input[type=text], input[type=email], input[type=search], textarea");

const showMessage = (field) => {
  // Remove the message we added before, then add a fresh one if the box is wrong.
  const old = field.parentElement.querySelector(`.js-feedback[data-for="${field.id}"]`);
  if (old) old.remove();
  if (field.validity.valid) return;

  const note = document.createElement("div");
  note.className = "invalid-feedback js-feedback";
  note.dataset.for = field.id;
  note.textContent = field.validationMessage;
  field.after(note);
};

postForms.forEach((form) => {
  form.setAttribute("novalidate", ""); // we show the messages ourselves

  form.addEventListener("submit", (event) => {
    if (event.defaultPrevented) return;

    // Delete / Remove / Undo forms: ask first, then send the form again once the person says yes.
    if (form.dataset.confirm && !confirmedForms.has(form)) {
      event.preventDefault();
      askConfirm(form.dataset.confirm, () => {
        confirmedForms.add(form);
        form.requestSubmit();
      });
      return;
    }
    confirmedForms.delete(form);

    // "  Plate  " becomes "Plate" before it is checked and sent.
    textBoxes(form).forEach((box) => {
      box.value = box.value.trim();
    });

    if (!form.checkValidity()) {
      event.preventDefault();
      form.classList.add("was-validated");
      form.querySelectorAll(":invalid").forEach((field) => {
        if (field.id) showMessage(field);
      });
      const first = form.querySelector(":invalid");
      if (first) first.focus();
      return;
    }

    // Valid: lock the buttons. setTimeout waits until the browser has read the form.
    setTimeout(() => {
      form.querySelectorAll("button[type=submit], input[type=submit]").forEach((button) => {
        button.disabled = true;
      });
    }, 0);
  });

  // Fix the message while typing, so it disappears as soon as the box is right.
  form.addEventListener("input", (event) => {
    const field = event.target;
    if (field.id && form.classList.contains("was-validated")) showMessage(field);
  });
});

// Coming back with the Back button must not leave the buttons locked.
window.addEventListener("pageshow", () => {
  document
    .querySelectorAll("form[method='POST'] button[type=submit], form[method='post'] button[type=submit]")
    .forEach((button) => {
      button.disabled = false;
    });
});

// ---------- Eye button on every password box (show / hide what you typed) ----------
// This does not decrypt anything: the box simply switches between type="password"
// (dots) and type="text" (readable). The password is still sent and stored hashed.
document.querySelectorAll("input[type='password']").forEach((input) => {
  // Wrap the input so the button can sit inside its right edge.
  const wrap = document.createElement("div");
  wrap.style.position = "relative";
  input.parentNode.insertBefore(wrap, input);
  wrap.appendChild(input);
  input.style.paddingRight = "2.75rem";

  const eyeOpen =
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  const eyeOff =
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17.94 17.94A10.9 10.9 0 0 1 12 20C5 20 1 12 1 12a18.5 18.5 0 0 1 5.06-5.94M9.9 4.24A9.1 9.1 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19M1 1l22 22"/></svg>';

  const button = document.createElement("button");
  button.type = "button"; // never submits the form
  button.className = "btn btn-link text-muted p-0";
  button.style.cssText = "position:absolute;top:50%;right:.75rem;transform:translateY(-50%);line-height:1;";
  button.setAttribute("aria-label", "Show password");
  button.innerHTML = eyeOpen;
  wrap.appendChild(button);

  button.addEventListener("click", () => {
    const hidden = input.type === "password";
    input.type = hidden ? "text" : "password";
    button.innerHTML = hidden ? eyeOff : eyeOpen;
    button.setAttribute("aria-label", hidden ? "Hide password" : "Show password");
  });
});

// Never leave a password readable after coming back with the Back button.
window.addEventListener("pageshow", () => {
  document.querySelectorAll("input[type='text'][autocomplete*='password']").forEach((i) => (i.type = "password"));
});
