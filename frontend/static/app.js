const $ = (id) => document.getElementById(id);

function showMessage(text) {
  const box = $("message");
  box.textContent = text;
  box.classList.remove("hidden");
  setTimeout(() => box.classList.add("hidden"), 5000);
}

async function api(url, options = {}) {
  const response = await fetch(url, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function loadScenario() {
  const [groups, shelters] = await Promise.all([api("/api/groups"), api("/api/shelters")]);
  $("groupCount").textContent = `${groups.length} groups`;
  $("shelterCount").textContent = `${shelters.length} shelters`;
  $("groupsBody").innerHTML = groups.map(g => `
    <tr><td><strong>${g.name}</strong></td><td>${g.people}</td>
    <td><span class="badge">${g.priority === 3 ? "Critical" : g.priority === 2 ? "High" : "Standard"}</span></td>
    <td>${g.special_requirements.length ? g.special_requirements.join(", ") : "None"}</td></tr>`).join("");
  $("sheltersBody").innerHTML = shelters.map(s => `
    <tr><td><strong>${s.name}</strong></td><td>${s.capacity}</td><td>${s.current_occupancy}</td>
    <td><span class="badge ${s.status}">${s.status}</span></td></tr>`).join("");
}

function renderResult(result) {
  const m = result.metrics;
  $("totalPeople").textContent = m.total_people;
  $("allocated").textContent = m.allocated_people;
  $("unallocated").textContent = m.unallocated_people;
  $("avgTravel").textContent = `${m.average_travel_distance.toFixed(2)} km`;
  $("runtime").textContent = `${m.runtime_ms.toFixed(2)} ms`;
  $("runStatus").textContent = `Run #${result.run_id} · ${result.status}`;
  $("allocationBody").innerHTML = result.allocations.length ? result.allocations.map(a => `
    <tr><td>${a.group_name}</td><td>${a.shelter_name}</td><td><strong>${a.people}</strong></td>
    <td>${a.distance.toFixed(2)} km</td><td>${a.priority}</td></tr>`).join("") : `<tr><td colspan="5">No allocations were produced.</td></tr>`;
  $("utilization").innerHTML = m.shelter_utilization.map(u => `
    <div class="util-card"><strong>${u.shelter_name}</strong><div>${u.allocated_people} allocated / ${u.remaining_capacity} usable capacity</div>
    <div class="bar"><div style="width:${Math.min(100, u.utilization * 100)}%"></div></div><small>${(u.utilization * 100).toFixed(1)}% utilization</small></div>`).join("");
  if (m.unallocated_people > 0) showMessage(`Optimization completed with ${m.unallocated_people} unallocated people. Review shelter capacity and eligibility.`);
}

$("optimizeBtn").addEventListener("click", async () => {
  const button = $("optimizeBtn");
  button.disabled = true; button.textContent = "Optimizing…";
  try {
    const result = await api("/api/optimize", { method: "POST", body: JSON.stringify({
      travel_weight: Number($("travelWeight").value),
      imbalance_weight: Number($("balanceWeight").value)
    }) });
    renderResult(result);
  } catch (err) { showMessage(err.message); }
  finally { button.disabled = false; button.textContent = "Run Optimization"; }
});

loadScenario().catch(err => showMessage(err.message));
