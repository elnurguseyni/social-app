async function submitForm(form) {
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

    return response.json();
}

document.querySelectorAll(".like-form").forEach((form) => {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const button = form.querySelector("button");
        const card = form.closest("article");
        const count = card.querySelector(".like-count");

        if (button.disabled) return;
        button.disabled = true;

        try {
            const result = await submitForm(form);
            button.textContent = result.liked ? "Unlike" : "Like";
            count.textContent = `${result.like_count} likes`;
        } catch (error) {
            alert("Could not confirm the update. Refresh the page to check the current like status.");
        } finally {
            button.disabled = false;
        }
    });
});

document.querySelectorAll(".comment-form").forEach((form) => {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const button = form.querySelector("button");
        const textarea = form.querySelector("textarea");
        const list = form.closest("article").querySelector(".comment-list");

        if (button.disabled) return;
        button.disabled = true;
        textarea.readOnly = true;

        try {
            const result = await submitForm(form);
            const fragment = document.createDocumentFragment();

            result.comments.forEach((comment) => {
                const paragraph = document.createElement("p");
                const author = document.createElement("strong");

                author.textContent = comment.username;
                paragraph.append(author, `: ${comment.content}`);
                fragment.append(paragraph);
            });

            list.replaceChildren(fragment);
            textarea.value = "";
        } catch (error) {
            alert("Could not confirm the comment was saved. Refresh the page before trying again to avoid posting it twice.");
        } finally {
            button.disabled = false;
            textarea.readOnly = false;
        }
    });
});

document.querySelectorAll(".edit-form").forEach((form) => {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const button = form.querySelector("button");
        const textarea = form.querySelector("textarea");
        const card = form.closest("article");
        const postContent = card.querySelector(".post-content");

        if (button.disabled) return;
        button.disabled = true;
        textarea.readOnly = true;

        try {
            const result = await submitForm(form);
            postContent.textContent = result.content;
            textarea.value = result.content;
        } catch (error) {
            alert("Could not confirm the edit was saved. Refresh the page to check the current post.");
        } finally {
            button.disabled = false;
            textarea.readOnly = false;
        }
    });
});