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
// Found by field NAME inside each form (not by id), so it also works in the Register pop-up.
document.querySelectorAll("form").forEach((form) => {
  const password = form.querySelector("input[name='password']");
  const confirmPassword = form.querySelector("input[name='confirm_password']");
  if (!password || !confirmPassword) return;

  const checkMatch = () => {
    const mismatch = confirmPassword.value && password.value !== confirmPassword.value;
    confirmPassword.setCustomValidity(mismatch ? "Passwords must match." : "");
  };
  password.addEventListener("input", checkMatch);
  confirmPassword.addEventListener("input", checkMatch);
});

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
  input.style.backgroundImage = "none"; // Bootstrap's red "!" icon would sit under the eye

  // A server error message sits right after the box. Keep it next to the box inside the wrapper,
  // otherwise Bootstrap would hide it (it only shows messages that are siblings of the box).
  let next = wrap.nextElementSibling;
  while (next && next.classList.contains("invalid-feedback")) {
    const after = next.nextElementSibling;
    wrap.appendChild(next);
    next = after;
  }

  const eyeOpen =
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  const eyeOff =
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17.94 17.94A10.9 10.9 0 0 1 12 20C5 20 1 12 1 12a18.5 18.5 0 0 1 5.06-5.94M9.9 4.24A9.1 9.1 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19M1 1l22 22"/></svg>';

  const button = document.createElement("button");
  button.type = "button"; // never submits the form
  button.className = "btn btn-link text-muted p-0";
  // The height of one text box, so the eye stays beside the box even when a message appears under it.
  button.style.cssText =
    "position:absolute;top:0;right:.75rem;height:calc(1.5em + .75rem + 2px);display:flex;align-items:center;line-height:1;";
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

// ---------- Feedback messages as a pop-up (like a browser notification) ----------
// The server sends messages such as "Equipment was added." as coloured bars at the top of the page.
// Here every one of them is moved into a single centred Bootstrap modal instead. The title and
// colour follow the most serious message. Without Bootstrap the bars simply stay as they are.
(() => {
  const bars = document.querySelectorAll("main > .alert, main > .container > .alert");
  if (!bars.length || !window.bootstrap) return;

  const rank = { danger: 0, warning: 1, success: 2, info: 3 };
  const titles = { danger: "Something went wrong", warning: "Please note", success: "Done", info: "Notice" };
  const colours = { danger: "danger", warning: "warning", success: "success", info: "primary" };

  let top = "info";
  const messages = [];
  bars.forEach((bar) => {
    const kind = Object.keys(rank).find((k) => bar.classList.contains("alert-" + k)) || "info";
    if (rank[kind] < rank[top]) top = kind;
    messages.push(bar.textContent.trim());
    bar.remove(); // the bar is gone; its text now lives in the pop-up
  });

  const box = document.createElement("div");
  box.className = "modal fade";
  box.tabIndex = -1;
  box.setAttribute("aria-labelledby", "feedbackTitle");
  box.setAttribute("aria-hidden", "true");
  box.innerHTML = `
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content" style="border:0;border-radius:1rem;border-top:5px solid var(--bs-${colours[top]});">
        <div class="modal-header border-0 pb-0">
          <h2 class="modal-title h5" id="feedbackTitle"></h2>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body"></div>
        <div class="modal-footer border-0 pt-0">
          <button type="button" class="btn btn-brand" data-bs-dismiss="modal">OK</button>
        </div>
      </div>
    </div>`;
  // textContent (not innerHTML): the messages can contain names typed by users.
  box.querySelector("#feedbackTitle").textContent = titles[top];
  const body = box.querySelector(".modal-body");
  messages.forEach((text) => {
    const p = document.createElement("p");
    p.className = "mb-2";
    p.textContent = text;
    body.appendChild(p);
  });
  document.body.appendChild(box);

  const modal = bootstrap.Modal.getOrCreateInstance(box);
  box.addEventListener("shown.bs.modal", () => box.querySelector(".btn-brand").focus());
  // Other scripts (the home page) can wait for this pop-up to close before opening theirs.
  window.caterFeedback = box;
  modal.show();
})();
