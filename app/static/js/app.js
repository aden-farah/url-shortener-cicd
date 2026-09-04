const form = document.getElementById("shorten-form");
const urlInput = document.getElementById("url-input");
const result = document.getElementById("result");
const shortUrl = document.getElementById("short-url");
const copyButton = document.getElementById("copy-button");
const errorMessage = document.getElementById("error-message");
const submitButton = form.querySelector('button[type="submit"]');

window.addEventListener("pageshow", () => {
    form.reset();
    urlInput.value = "";
    result.classList.add("hidden");
    errorMessage.textContent = "";
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    result.classList.add("hidden");
    errorMessage.textContent = "";
    submitButton.disabled = true;
    submitButton.textContent = "Shortening...";

    try {
        const response = await fetch("/shorten", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                url: urlInput.value.trim(),
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            let message = "Could not shorten this URL.";

            if (Array.isArray(data.detail) && data.detail[0]?.msg) {
                message = data.detail[0].msg;
            } else if (typeof data.detail === "string") {
                message = data.detail;
            }

            throw new Error(message);
        }

        shortUrl.textContent = data.short_url;
        shortUrl.href = data.short_url;
        result.classList.remove("hidden");
    } catch (error) {
        errorMessage.textContent =
            error.message || "Something went wrong. Please try again.";
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = "Shorten";
    }
});

copyButton.addEventListener("click", async () => {
    try {
        await navigator.clipboard.writeText(shortUrl.href);

        copyButton.textContent = "Copied!";
        errorMessage.textContent = "";

        setTimeout(() => {
            copyButton.textContent = "Copy";
        }, 1500);
    } catch {
        errorMessage.textContent =
            "Could not copy the link. Please copy it manually.";
    }
});