/* ============================================================================
   ROCK CORPORATION - SCRIPT UNICO Y OPTIMIZADO (SINGLE JS FILE)
   ============================================================================ */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Manejo ultra ligero de Notificaciones (Toasts)
    function iniciarNotificaciones() {
        document.querySelectorAll(".flash, .message").forEach((alert) => {
            if (!alert.querySelector(".flash-close-btn")) {
                const closeBtn = document.createElement("button");
                closeBtn.type = "button";
                closeBtn.className = "flash-close-btn";
                closeBtn.setAttribute("aria-label", "Cerrar");
                closeBtn.innerHTML = '<i class="fa-solid fa-xmark"></i>';
                closeBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    ocultarAlerta();
                });
                alert.appendChild(closeBtn);
            }

            let hideTimeout = null;

            const ocultarAlerta = () => {
                if (!alert.isConnected || alert.classList.contains("hide")) {
                    return;
                }
                alert.classList.add("hide");
                window.setTimeout(() => {
                    if (alert.isConnected) {
                        alert.remove();
                    }
                }, 300);
            };

            const iniciarTimer = (delay = 8500) => {
                if (hideTimeout) window.clearTimeout(hideTimeout);
                hideTimeout = window.setTimeout(ocultarAlerta, delay);
            };

            alert.addEventListener("mouseenter", () => {
                if (hideTimeout) window.clearTimeout(hideTimeout);
            });

            alert.addEventListener("mouseleave", () => {
                iniciarTimer(4000);
            });

            iniciarTimer(8500);
        });
    }

    // 2. Tablas responsivas automáticas
    document.querySelectorAll("table").forEach((table) => {
        if (!table.parentElement.classList.contains("table-responsive")) {
            const wrapper = document.createElement("div");
            wrapper.className = "table-responsive";
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
    });

    // 3. Confirmación de acciones destructivas
    document.querySelectorAll("a[href*='eliminar'], a[href*='prohibir']").forEach((link) => {
        link.addEventListener("click", (event) => {
            if (!window.confirm("¿Confirma esta acción antes de continuar?")) {
                event.preventDefault();
            }
        });
    });

    document.querySelectorAll("form").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const action = form.getAttribute("action") || "";
            const needsConfirmation = ["eliminar", "prohibir", "reportar"].some((word) => action.includes(word));

            if (needsConfirmation && !window.confirm("¿Confirma esta acción antes de continuar?")) {
                event.preventDefault();
            }
        });
    });

    // 4. Submit automático en selectores
    document.querySelectorAll("select[data-autosubmit='true']").forEach((select) => {
        select.addEventListener("change", () => {
            select.form?.requestSubmit();
        });
    });

    iniciarNotificaciones();
});
