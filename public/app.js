const loginView = document.getElementById("loginView");
const mainView = document.getElementById("mainView");
const loginForm = document.getElementById("loginForm");
const loginError = document.getElementById("loginError");
const greeting = document.getElementById("greeting");
const logoutBtn = document.getElementById("logoutBtn");

function showLogin(msg = "") {
  loginView.style.display = "";
  mainView.style.display = "none";
  loginError.textContent = msg;
}

function showMain(message) {
  loginView.style.display = "none";
  mainView.style.display = "";
  greeting.textContent = message;
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    // IMPORTANT: send/receive cookies
    credentials: "include",
  });
  return res;
}

async function boot() {
  // If already logged in, greet user
  const res = await api("/api/me", { method: "GET" });
  if (res.ok) {
    const data = await res.json();
    showMain(data.message);
  } else {
    showLogin("");
  }
}

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  loginError.textContent = "";

  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  const res = await api("/api/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const txt = await res.text();
    showLogin(txt || "Login failed");
    return;
  }

  const me = await api("/api/me", { method: "GET" });
  if (me.ok) {
    const data = await me.json();
    showMain(data.message);
  } else {
    showLogin("Logged in, but session not recognized");
  }
});

logoutBtn.addEventListener("click", async () => {
  await api("/api/logout", { method: "POST", body: "{}" });
  showLogin("");
});

boot();
