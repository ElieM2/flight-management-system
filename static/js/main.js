/* =========================================================
   FLIGHTLOGOS - GLOBAL UI CONTROLLER
   Unified theme + clean navigation state
========================================================= */

(function () {
    "use strict";

    const STORAGE_KEY = "logosflight-theme";
    const LIGHT_THEME = "light";
    const DARK_THEME = "dark";

    function ready(callback) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", callback);
        } else {
            callback();
        }
    }

    function qs(selector, parent = document) {
        return parent.querySelector(selector);
    }

    function qsa(selector, parent = document) {
        return Array.from(parent.querySelectorAll(selector));
    }

    function normalizePath(path) {
        if (!path) {
            return "/";
        }

        let cleanPath = path.split("?")[0].split("#")[0];

        if (!cleanPath.startsWith("/")) {
            cleanPath = "/" + cleanPath;
        }

        if (cleanPath.length > 1 && cleanPath.endsWith("/")) {
            cleanPath = cleanPath.slice(0, -1);
        }

        return cleanPath;
    }

    function isMapPage() {
        const currentPath = normalizePath(window.location.pathname);

        return Boolean(qs(".lf-map-page")) || currentPath === "/monitoring/map";
    }

    function normalizeTheme(theme) {
        return theme === LIGHT_THEME ? LIGHT_THEME : DARK_THEME;
    }

    function getStoredTheme() {
        try {
            return localStorage.getItem(STORAGE_KEY);
        } catch (error) {
            return null;
        }
    }

    function saveTheme(theme) {
        try {
            localStorage.setItem(STORAGE_KEY, normalizeTheme(theme));
        } catch (error) {
            return;
        }
    }

    function getPreferredTheme() {
        const storedTheme = getStoredTheme();

        if (storedTheme === LIGHT_THEME || storedTheme === DARK_THEME) {
            return storedTheme;
        }

        return LIGHT_THEME;
    }

    function setThemeButtonState(theme) {
        const safeTheme = normalizeTheme(theme);

        const themeButtons = qsa(
            ".theme-toggle, .ops-theme-toggle, [data-theme-toggle], #themeToggle, #opsThemeToggle"
        );

        themeButtons.forEach(function (button) {
            button.setAttribute(
                "aria-label",
                safeTheme === DARK_THEME ? "Switch to light mode" : "Switch to dark mode"
            );

            button.setAttribute(
                "title",
                safeTheme === DARK_THEME ? "Switch to light mode" : "Switch to dark mode"
            );

            button.dataset.currentTheme = safeTheme;

            const icon = button.querySelector("i");

            if (icon) {
                icon.className = safeTheme === DARK_THEME ? "bi bi-moon-stars" : "bi bi-sun";
            }

            const text = button.querySelector("[data-theme-text]");

            if (text) {
                text.textContent = safeTheme === DARK_THEME ? "Dark" : "Light";
            }
        });
    }

    function applyMapSafeTheme(theme) {
        const safeTheme = normalizeTheme(theme);

        document.body.classList.add("logosflight-map-mode");

        if (safeTheme === LIGHT_THEME) {
            document.body.classList.add("logosflight-map-light-ui");
            document.body.classList.remove("logosflight-map-dark-ui");
        } else {
            document.body.classList.add("logosflight-map-dark-ui");
            document.body.classList.remove("logosflight-map-light-ui");
        }
    }

    function removeMapSafeTheme() {
        document.body.classList.remove("logosflight-map-mode");
        document.body.classList.remove("logosflight-map-light-ui");
        document.body.classList.remove("logosflight-map-dark-ui");
    }

    function applyTheme(theme) {
        const safeTheme = normalizeTheme(theme);

        document.documentElement.setAttribute("data-theme", safeTheme);
        document.body.setAttribute("data-theme", safeTheme);

        document.documentElement.classList.toggle("theme-dark", safeTheme === DARK_THEME);
        document.documentElement.classList.toggle("theme-light", safeTheme === LIGHT_THEME);
        document.documentElement.classList.toggle("dark-mode", safeTheme === DARK_THEME);
        document.documentElement.classList.toggle("light-mode", safeTheme === LIGHT_THEME);
        document.documentElement.classList.toggle("is-dark", safeTheme === DARK_THEME);
        document.documentElement.classList.toggle("is-light", safeTheme === LIGHT_THEME);

        document.body.classList.toggle("theme-dark", safeTheme === DARK_THEME);
        document.body.classList.toggle("theme-light", safeTheme === LIGHT_THEME);
        document.body.classList.toggle("dark-mode", safeTheme === DARK_THEME);
        document.body.classList.toggle("light-mode", safeTheme === LIGHT_THEME);
        document.body.classList.toggle("is-dark", safeTheme === DARK_THEME);
        document.body.classList.toggle("is-light", safeTheme === LIGHT_THEME);

        if (isMapPage()) {
            applyMapSafeTheme(safeTheme);
        } else {
            removeMapSafeTheme();
        }

        setThemeButtonState(safeTheme);

        try {
            const eventPayload = {
                detail: {
                    theme: safeTheme,
                    mapPage: isMapPage()
                }
            };

            document.dispatchEvent(new CustomEvent("logosflight:theme-change", eventPayload));
            window.dispatchEvent(new CustomEvent("logosflight:theme-change", eventPayload));
        } catch (error) {
            return;
        }
    }

    function toggleTheme() {
        const currentTheme =
            document.documentElement.getAttribute("data-theme") ||
            document.body.getAttribute("data-theme") ||
            getPreferredTheme();

        const nextTheme = normalizeTheme(currentTheme) === DARK_THEME ? LIGHT_THEME : DARK_THEME;

        saveTheme(nextTheme);
        applyTheme(nextTheme);
    }

    function closeAllDropdowns(exceptElement = null) {
        qsa(".language-switcher.is-open, .ops-language.is-open").forEach(function (item) {
            if (exceptElement && item === exceptElement) {
                return;
            }

            item.classList.remove("is-open");

            const trigger = item.querySelector(
                ".language-switcher__trigger, .ops-language-trigger, [data-language-trigger]"
            );

            if (trigger) {
                trigger.setAttribute("aria-expanded", "false");
            }
        });

        qsa(".private-profile-dropdown.is-open, .ops-user.is-open").forEach(function (item) {
            if (exceptElement && item === exceptElement) {
                return;
            }

            item.classList.remove("is-open");
        });

        qsa(".notification-dropdown.is-open, .notification-menu.is-open").forEach(function (item) {
            if (exceptElement && item === exceptElement) {
                return;
            }

            item.classList.remove("is-open");
        });
    }

    function initPublicNavigation() {
        const navToggle = qs("#navToggle");
        const publicNav = qs("#publicNav");

        if (navToggle && publicNav) {
            navToggle.addEventListener("click", function (event) {
                event.preventDefault();

                publicNav.classList.toggle("is-open");
                navToggle.classList.toggle("is-active", publicNav.classList.contains("is-open"));
            });
        }

        const megaItems = qsa(".nav-mega-item");

        megaItems.forEach(function (item) {
            const link = item.querySelector(":scope > a");
            const menu = item.querySelector(".mega-menu");

            if (!link || !menu) {
                return;
            }

            link.addEventListener("click", function (event) {
                if (window.innerWidth <= 1200) {
                    event.preventDefault();

                    megaItems.forEach(function (otherItem) {
                        if (otherItem !== item) {
                            otherItem.classList.remove("mega-open");
                        }
                    });

                    item.classList.toggle("mega-open");
                }
            });
        });
    }

    function initPrivateNavigation() {
        const menuButton = qs("#enterpriseMenuButton");
        const header = qs(".enterprise-header");

        if (menuButton && header) {
            menuButton.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();

                header.classList.toggle("is-open");
                menuButton.classList.toggle("is-active", header.classList.contains("is-open"));
            });
        }

        document.addEventListener("click", function (event) {
            if (!header || !header.classList.contains("is-open")) {
                return;
            }

            if (header.contains(event.target)) {
                return;
            }

            header.classList.remove("is-open");

            if (menuButton) {
                menuButton.classList.remove("is-active");
            }
        });

        window.addEventListener("resize", function () {
            if (window.innerWidth > 1380 && header) {
                header.classList.remove("is-open");

                if (menuButton) {
                    menuButton.classList.remove("is-active");
                }
            }
        });
    }

    function initLanguageSwitcher() {
        const switchers = qsa(".language-switcher, .ops-language");

        switchers.forEach(function (switcher) {
            const trigger =
                switcher.querySelector(".language-switcher__trigger") ||
                switcher.querySelector(".ops-language-trigger") ||
                switcher.querySelector("[data-language-trigger]");

            if (!trigger) {
                return;
            }

            trigger.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();

                const willOpen = !switcher.classList.contains("is-open");

                closeAllDropdowns(switcher);

                switcher.classList.toggle("is-open", willOpen);
                trigger.setAttribute("aria-expanded", willOpen ? "true" : "false");
            });
        });
    }

    function initProfileDropdown() {
        const dropdowns = qsa(".private-profile-dropdown, .ops-user");

        dropdowns.forEach(function (dropdown) {
            const trigger =
                dropdown.querySelector(".private-profile-trigger") ||
                dropdown.querySelector(".ops-user-trigger") ||
                dropdown.querySelector("[data-profile-trigger]");

            if (!trigger) {
                return;
            }

            trigger.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();

                const willOpen = !dropdown.classList.contains("is-open");

                closeAllDropdowns(dropdown);

                dropdown.classList.toggle("is-open", willOpen);
            });
        });
    }

    function initNotificationDropdown() {
        const notificationButtons = qsa(".notification-button, [data-notification-trigger]");

        notificationButtons.forEach(function (button) {
            const wrapper =
                button.closest(".notification-dropdown") ||
                button.closest(".notification-menu") ||
                button.parentElement;

            if (!wrapper) {
                return;
            }

            button.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();

                const willOpen = !wrapper.classList.contains("is-open");

                closeAllDropdowns(wrapper);

                wrapper.classList.toggle("is-open", willOpen);
            });
        });
    }

    function initThemeSwitcher() {
        const initialTheme = getPreferredTheme();

        applyTheme(initialTheme);

        const themeButtons = qsa(
            ".theme-toggle, .ops-theme-toggle, [data-theme-toggle], #themeToggle, #opsThemeToggle"
        );

        themeButtons.forEach(function (button) {
            button.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();

                toggleTheme();
            });
        });
    }

    function initKeyboardClose() {
        document.addEventListener("keydown", function (event) {
            if (event.key !== "Escape") {
                return;
            }

            closeAllDropdowns();

            const header = qs(".enterprise-header");
            const menuButton = qs("#enterpriseMenuButton");

            if (header) {
                header.classList.remove("is-open");
            }

            if (menuButton) {
                menuButton.classList.remove("is-active");
            }
        });
    }

    function initOutsideClickClose() {
        document.addEventListener("click", function () {
            closeAllDropdowns();
        });

        qsa(
            ".language-switcher, .private-profile-dropdown, .notification-dropdown, .notification-menu, .ops-language, .ops-user"
        ).forEach(function (element) {
            element.addEventListener("click", function (event) {
                event.stopPropagation();
            });
        });
    }

    function setActiveNavigationLink(link) {
        qsa(".enterprise-nav a, .ops-main-nav a").forEach(function (item) {
            item.classList.remove("is-active");
        });

        if (link) {
            link.classList.add("is-active");
        }
    }

    function initActiveNavigationFallback() {
        const currentPath = normalizePath(window.location.pathname);
        const links = qsa(".enterprise-nav a, .ops-main-nav a");

        if (!links.length) {
            return;
        }

        let activeLink = null;

        links.forEach(function (link) {
            const href = normalizePath(link.getAttribute("href"));

            if (currentPath === href) {
                activeLink = link;
            }
        });

        if (!activeLink) {
            links.forEach(function (link) {
                const href = normalizePath(link.getAttribute("href"));

                if (currentPath === "/monitoring/map" && href === "/monitoring/map") {
                    activeLink = link;
                }

                if (currentPath === "/monitoring" && href === "/monitoring") {
                    activeLink = link;
                }

                if (currentPath.startsWith("/analytics") && href === "/analytics") {
                    activeLink = link;
                }

                if (currentPath.startsWith("/sync") && href === "/sync") {
                    activeLink = link;
                }

                if (currentPath.startsWith("/dashboard") && href === "/dashboard") {
                    activeLink = link;
                }
            });
        }

        setActiveNavigationLink(activeLink);
    }

    function initMapPageSafety() {
        if (!isMapPage()) {
            return;
        }

        const currentTheme =
            document.documentElement.getAttribute("data-theme") ||
            document.body.getAttribute("data-theme") ||
            getPreferredTheme();

        applyMapSafeTheme(currentTheme);
    }

    ready(function () {
        initThemeSwitcher();

        initPublicNavigation();
        initPrivateNavigation();

        initLanguageSwitcher();
        initProfileDropdown();
        initNotificationDropdown();

        initOutsideClickClose();
        initKeyboardClose();

        initActiveNavigationFallback();
        initMapPageSafety();
    });
})();

// flightlogos-theme-cleanup
(function () {
    try {
        if (!localStorage.getItem("flightlogos-theme")) {
            localStorage.setItem("flightlogos-theme", "dark");
        }

        localStorage.removeItem("flightlogosPublicTheme");
        localStorage.removeItem("logosflight-theme");

        const theme = localStorage.getItem("flightlogos-theme") === "light" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", theme);
    } catch (error) {}
})();