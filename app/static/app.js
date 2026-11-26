// Shared front-end helpers. Every action goes through our own JSON API under /api/v1.

async function api(path, options = {}) {
    const response = await fetch(`/api/v1${path}`, {
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin", // send the HttpOnly login cookie
        ...options,
    });
    const data = response.status === 204 ? null : await response.json().catch(() => null);
    if (!response.ok) {
        throw new Error(errorMessage(data, response.status));
    }
    return data;
}


function errorMessage(data, status) {
    if (data && typeof data.detail === "string") return data.detail;
    if (data && Array.isArray(data.detail)) return data.detail.map((e) => e.msg).join(", ");
    if (status === 401) return "Please log in first";
    if (status === 429) return "Too many attempts, please wait a minute";
    return "Something went wrong, please try again";
}

function showMessage(text, isError = false) {
    const box = document.getElementById("message");
    // textContent (never innerHTML) means server text is shown as text and can't run as code
    box.textContent = text;
    box.className = isError ? "message error" : "message success";
    box.hidden = false;
    box.scrollIntoView({ behavior: "smooth", block: "center"});
}

//any <form data-api="/path"> is sent top that API endpoint as JSON
document.querySelectorAll("form[data-api]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const body = Object.fromEntries(new FormData(form));

        // Leave out empty optional fiels, such as a review with no comment
        for (const key of Object.keys(body)) {
            if (body[key] === "") delete body[key];
        }
        // Form values are always text; convert fields markes data-number into numbers
        form.querySelectorAll("[data-number]").forEach((input) => {
            if (input.name in body) body[input.name] = Number(body[input.name]);
        });

        try {
            await api(form.dataset.api, {
                method: form.dataset.method || "POST",
                body: JSON.stringify(body),
            });
            if (form.dataset.redirect) {
                window.location.href = form.dataset.redirect;
            } else {
                showMessage(form.dataset.success || "Done!");
            }
        } catch (error) {
            showMessage(error.message, true);
        }
    });
});

document.getElementById("logout")?.addEventListener("click", async () => {
    await api("/auth/logout", { method: "POST" });
    window.location.href = "/";
})