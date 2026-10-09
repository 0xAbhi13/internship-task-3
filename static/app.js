// confirm deletes, deadline highlight
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-confirm]").forEach(f => {
    f.addEventListener("submit", e => {
      if (!confirm(f.dataset.confirm || "Are you sure?")) e.preventDefault();
    });
  });
});
