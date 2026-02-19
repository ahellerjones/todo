const loginView = document.getElementById("loginView");
const mainView = document.getElementById("mainView");
const loginForm = document.getElementById("loginForm");
const loginError = document.getElementById("loginError");
const greeting = document.getElementById("greeting");
const logoutBtn = document.getElementById("logoutBtn");

const todoForm = document.getElementById("todoForm");
const todoText = document.getElementById("todoText");
const todoError = document.getElementById("todoError");
const todoList = document.getElementById("todoList");

const showSignupBtn = document.getElementById("showSignupBtn");
const signupForm = document.getElementById("signupForm");
const cancelSignupBtn = document.getElementById("cancelSignupBtn");
const newUsername = document.getElementById("newUsername");
const newPassword = document.getElementById("newPassword");

function showLogin(msg = "") {
  loginView.style.display = "";
  mainView.style.display = "none";
  loginError.textContent = msg;
  if (signupForm) hideSignup();
}

function showSignup() {
  signupForm.style.display = "";
  showSignupBtn.style.display = "none";
  loginError.textContent = "";
  newUsername.value = "";
  newPassword.value = "";
  newUsername.focus();
}

function hideSignup() {
  signupForm.style.display = "none";
  showSignupBtn.style.display = "";
  loginError.textContent = "";
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
    credentials: "include",
  });
  return res;
}

function renderTodos(todos) {
  todoList.innerHTML = "";

  for (const t of todos) {
    const li = document.createElement("li");
    li.className = "todo";

    const left = document.createElement("div");
    left.className = "todo-left";

    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = !!t.completed;
    cb.addEventListener("change", async () => {
      await api(`/api/todos/${t.id}`, {
        method: "PATCH",
        body: JSON.stringify({ completed: cb.checked }),
      });
      await loadTodos();
    });

    const text = document.createElement("span");
    text.textContent = t.text;
    if (t.completed) text.className = "done";

    // click text to edit
    text.addEventListener("click", () => {
      const input = document.createElement("input");
      input.value = t.text;
      input.className = "edit";

      const save = async () => {
        const newText = input.value.trim();
        if (!newText) return;
        await api(`/api/todos/${t.id}`, {
          method: "PATCH",
          body: JSON.stringify({ text: newText }),
        });
        await loadTodos();
      };

      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") save();
        if (e.key === "Escape") loadTodos();
      });
      input.addEventListener("blur", save);

      text.replaceWith(input);
      input.focus();
      input.select();
    });

    left.appendChild(cb);
    left.appendChild(text);

    const del = document.createElement("button");
    del.textContent = "Delete";
    del.addEventListener("click", async () => {
      await api(`/api/todos/${t.id}`, { method: "DELETE" });
      await loadTodos();
    });

    li.appendChild(left);
    li.appendChild(del);

    todoList.appendChild(li);
  }
}

async function loadTodos() {
  todoError.textContent = "";
  const res = await api("/api/todos", { method: "GET" });
  if (!res.ok) {
    const txt = await res.text();
    todoError.textContent = txt || "Failed to load todos";
    renderTodos([]);
    return;
  }
  const data = await res.json();
  renderTodos(data.todos || []);
}

async function createTodo(text) {
  todoError.textContent = "";
  const res = await api("/api/todos", {
    method: "POST",
    body: JSON.stringify({ text }),
  });

  if (!res.ok) {
    const txt = await res.text();
    todoError.textContent = txt || "Failed to create todo";
    return false;
  }
  return true;
}

async function boot() {
  const res = await api("/api/me", { method: "GET" });
  if (res.ok) {
    const data = await res.json();
    showMain(data.message);
    await loadTodos();
  } else {
    showLogin("");
  }
}

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  loginError.textContent = "";

  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  if (!username || !password) {
    loginError.textContent = "Missing username or password";
    return;
  }

  const res = await api("/api/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    // Best-effort parse error message
    let msg = "Login failed";
    const ct = res.headers.get("content-type") || "";

    try {
      if (ct.includes("application/json")) {
        const data = await res.json();
        msg = data.error || data.message || msg;
      } else {
        const txt = (await res.text()).trim();
        if (txt) msg = txt;
      }
    } catch (_) {
      // ignore parse errors
    }

    if (res.status === 401 && msg === "Login failed") {
      msg = "Invalid username or password";
    }

    loginError.textContent = msg;
    return;
  }

  // Success: confirm session + load UI
  const me = await api("/api/me", { method: "GET" });
  if (!me.ok) {
    const txt = (await me.text()).trim();
    loginError.textContent = txt || "Logged in, but session not recognized";
    return;
  }

  const data = await me.json();
  showMain(data.message);
  await loadTodos();
});

todoForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = (todoText.value || "").trim();
  if (!text) return;

  const ok = await createTodo(text);
  if (!ok) return;

  todoText.value = "";
  await loadTodos();
});

logoutBtn.addEventListener("click", async () => {
  await api("/api/logout", { method: "POST", body: "{}" });
  renderTodos([]);
  showLogin("");
});

showSignupBtn.addEventListener("click", showSignup);
cancelSignupBtn.addEventListener("click", hideSignup);

signupForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  loginError.textContent = "";

  const username = (newUsername.value || "").trim();
  const password = newPassword.value || "";

  if (!username || !password) {
    loginError.textContent = "Missing username or password";
    return;
  }

  // Create user
  const createRes = await api("/api/users", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

  if (!createRes.ok) {
    const txt = await createRes.text();
    loginError.textContent = txt || "Failed to create user";
    return;
  }

  // Auto-login after signup
  const loginRes = await api("/api/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

  if (!loginRes.ok) {
    const txt = await loginRes.text();
    loginError.textContent = txt || "Account created, but login failed";
    hideSignup();
    return;
  }

  hideSignup();

  const me = await api("/api/me", { method: "GET" });
  if (me.ok) {
    const data = await me.json();
    showMain(data.message);
    await loadTodos();
  } else {
    showLogin("Signed up, but session not recognized");
  }
});

boot();