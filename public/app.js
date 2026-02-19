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
    credentials: "include",
  });
  return res;
}

function renderTodos(todos) {
  todoList.innerHTML = "";
  for (const t of todos) {
    const li = document.createElement("li");
    li.textContent = t.completed ? `✅ ${t.text}` : t.text;
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
    await loadTodos();
  } else {
    showLogin("Logged in, but session not recognized");
  }
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

boot();