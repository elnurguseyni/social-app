document.querySelectorAll(".like-form").forEach((form) => {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const button = form.querySelector("button");
        const card = form.closest("article");
        const count = card.querySelector(".like-count");

        if (button.disabled) return;
        button.disabled = true;

        try {
            const response = await fetch(form.action, {
                method: "POST",
                headers: {
                    Accept: "application/json",
                },
                body: new FormData(form),
            });

            if (
                !response.ok ||
                response.redirected ||
                !response.headers.get("content-type")?.includes("application/json")
            ) {
                throw new Error("Unexpected response");
            }

            const result = await response.json();

            button.textContent = result.liked ? "Unlike" : "Like";
            count.textContent = `${result.like_count} likes`;
        } catch (error) {
            alert("Could not confirm the update. Refresh the page to check the current like status.");
        } finally {
            button.disabled = false;
        }
    });
});