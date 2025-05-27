document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("city-input");
  const suggestions = document.getElementById("suggestions");

  input.addEventListener("input", async () => {
    const query = input.value.trim();
    if (query.length < 2) {
      suggestions.innerHTML = "";
      return;
    }

    const res = await fetch(`/autocomplete?q=${encodeURIComponent(query)}`);
    if (!res.ok) {
      suggestions.innerHTML = "";
      return;
    }
    const cities = await res.json();

    suggestions.innerHTML = "";
    cities.forEach(city => {
      const div = document.createElement("div");
      div.textContent = city;
      div.classList.add("suggestion-item");
      div.addEventListener("click", () => {
        input.value = city;
        suggestions.innerHTML = "";
      });
      suggestions.appendChild(div);
    });
  });

  // По клику вне подсказок — скрыть их
  document.addEventListener("click", (e) => {
    if (!suggestions.contains(e.target) && e.target !== input) {
      suggestions.innerHTML = "";
    }
  });
});
