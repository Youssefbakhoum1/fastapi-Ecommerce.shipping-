document.addEventListener("DOMContentLoaded", () => {
    const root = document.documentElement;
    const themeToggle = document.getElementById("theme-toggle");

    const applyTheme = (theme) => {
        root.dataset.theme = theme;
        localStorage.setItem("myshop-theme", theme);
        if (themeToggle) {
            themeToggle.innerHTML = theme === "dark"
                ? '<i class="bi bi-sun-fill"></i>'
                : '<i class="bi bi-moon-stars-fill"></i>';
            themeToggle.title = theme === "dark" ? "Switch to light mode" : "Switch to dark mode";
        }
    };

    applyTheme(localStorage.getItem("myshop-theme") || "light");

    themeToggle?.addEventListener("click", () => {
        applyTheme(root.dataset.theme === "dark" ? "light" : "dark");
    });

    document.querySelectorAll(".password-toggle").forEach((button) => {
        button.addEventListener("click", () => {
            const input = document.getElementById(button.dataset.target);
            if (!input) return;
            const isPassword = input.type === "password";
            input.type = isPassword ? "text" : "password";
            button.innerHTML = isPassword ? '<i class="bi bi-eye-slash"></i>' : '<i class="bi bi-eye"></i>';
        });
    });

    const search = document.getElementById("product-search");
    const category = document.getElementById("category-filter");
    const items = [...document.querySelectorAll(".product-item")];

    const filterProducts = () => {
        const query = (search?.value || "").trim().toLowerCase();
        const selected = (category?.value || "all").toLowerCase();

        items.forEach((item) => {
            const name = item.dataset.name || "";
            const cat = item.dataset.category || "";
            const visible = name.includes(query) && (selected === "all" || cat === selected);
            item.style.display = visible ? "" : "none";
        });
    };

    search?.addEventListener("input", filterProducts);
    category?.addEventListener("change", filterProducts);

    const cartBadge = document.getElementById("cart-count");
    if (cartBadge) {
        fetch("/api/cart/count")
            .then((response) => response.ok ? response.json() : null)
            .then((data) => {
                if (!data) return;
                cartBadge.textContent = data.count;
                cartBadge.style.display = data.count > 0 ? "grid" : "none";
            })
            .catch(() => {});
    }
});
