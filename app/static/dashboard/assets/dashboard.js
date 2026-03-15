const REFRESH_INTERVAL_MS = 15000;

const state = {
  timerId: null,
  isFetching: false,
  data: null,
  page: 0,
  pageSize: 10,
};

const elements = {
  kpiGrid: document.getElementById("kpi-grid"),
  outcomeChart: document.getElementById("outcome-chart"),
  sentimentChart: document.getElementById("sentiment-chart"),
  loadStatusChart: document.getElementById("load-status-chart"),
  deltaSummary: document.getElementById("delta-summary"),
  callsTableBody: document.getElementById("calls-table-body"),
  pagination: document.getElementById("pagination"),
  lastUpdated: document.getElementById("last-updated"),
  fetchStatus: document.getElementById("fetch-status"),
  staleWarning: document.getElementById("stale-warning"),
  refreshButton: document.getElementById("refresh-button"),
};

function formatNumber(value) {
  return new Intl.NumberFormat("en-US").format(value ?? 0);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatCurrency(value) {
  if (value === null || value === undefined) {
    return "N/A";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPercent(value) {
  return `${Number(value ?? 0).toFixed(2)}%`;
}

function formatDateTime(value) {
  if (!value) {
    return "Not completed";
  }

  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function sentenceCase(value) {
  if (!value) {
    return "Unknown";
  }

  return String(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function renderKpis(summary) {
  const totalCalls = summary.total_calls ?? 0;
  const agreements = summary.agreements ?? 0;
  const avgDelta = summary.average_agreed_vs_listed_delta;

  const agreementsSubtext =
    totalCalls > 0
      ? `${agreements} of ${totalCalls} calls (${formatPercent((agreements / totalCalls) * 100)})`
      : `${agreements} of ${totalCalls} calls`;

  const cards = [
    { label: "Total calls", value: formatNumber(totalCalls) },
    {
      label: "Agreements",
      value: formatNumber(agreements),
      subtext: agreementsSubtext,
    },
    {
      label: "Net rate delta",
      value: formatCurrency(summary.total_agreed_vs_listed_delta),
      subtext: avgDelta !== null && avgDelta !== undefined
        ? `Avg per deal: ${formatCurrency(avgDelta)}`
        : "No deals yet",
    },
  ];

  elements.kpiGrid.innerHTML = cards
    .map(
      (card) => `
        <article class="kpi-card">
          <p class="kpi-label">${escapeHtml(card.label)}</p>
          <p class="kpi-value">${escapeHtml(card.value)}</p>
          ${card.subtext ? `<p class="kpi-subtext">${escapeHtml(card.subtext)}</p>` : ""}
        </article>
      `,
    )
    .join("");
}

function renderBars(container, items) {
  const entries = Array.isArray(items) ? items : [];

  if (entries.length === 0) {
    container.innerHTML = '<p class="empty-state">No data recorded yet.</p>';
    return;
  }

  const known = entries.filter((item) => item.label !== "unknown");
  const unknownEntry = entries.find((item) => item.label === "unknown");
  const total = known.reduce((sum, item) => sum + item.count, 0);

  const barsHtml = known
    .sort((a, b) => b.count - a.count)
    .map((item) => {
      const pct = total > 0 ? (item.count / total) * 100 : 0;
      const width = Math.max(pct, item.count > 0 ? 4 : 0);
      return `
        <div class="chart-row">
          <div class="chart-meta">
            <span class="chart-label">${escapeHtml(sentenceCase(item.label))}</span>
            <span class="chart-value">${escapeHtml(formatNumber(item.count))}</span>
          </div>
          <div class="chart-track" aria-hidden="true">
            <div class="chart-fill tone-${item.tone}" style="width:${width}%"></div>
          </div>
        </div>
      `;
    })
    .join("");

  const footnote = unknownEntry && unknownEntry.count > 0
    ? `<p class="chart-footnote">${unknownEntry.count} unclassified</p>`
    : "";

  container.innerHTML = barsHtml + footnote;
}

const TONE_COLORS = {
  positive: "#059669",
  negative: "#dc2626",
  pending: "#d97706",
};

function renderPie(container, items) {
  const entries = Array.isArray(items) ? items : [];

  if (entries.length === 0) {
    container.innerHTML = '<p class="empty-state">No data recorded yet.</p>';
    return;
  }

  const sorted = [...entries].sort((a, b) => b.count - a.count);
  const total = sorted.reduce((sum, item) => sum + item.count, 0);
  const hasData = total > 0;

  let cumulative = 0;
  const stops = hasData
    ? sorted.flatMap((item) => {
      const color = TONE_COLORS[item.tone] || TONE_COLORS.pending;
      const start = cumulative;
      cumulative += (item.count / total) * 100;
      return [`${color} ${start}% ${cumulative}%`];
    })
    : [];

  const legend = sorted
    .map((item) => {
      const color = TONE_COLORS[item.tone] || TONE_COLORS.pending;
      return `
        <div class="pie-legend-row">
          <span class="pie-swatch" style="background:${color}"></span>
          <span class="pie-legend-label">${escapeHtml(sentenceCase(item.label))}</span>
          <span class="pie-legend-value">${escapeHtml(formatNumber(item.count))}</span>
        </div>
      `;
    })
    .join("");

  container.innerHTML = `
    <div class="pie-layout">
      <div class="pie-ring" style="background:${hasData ? `conic-gradient(${stops.join(", ")})` : "var(--border-subtle)"}">
        <div class="pie-hole">
          <span class="pie-total">${formatNumber(total)}</span>
        </div>
      </div>
      <div class="pie-legend">${legend}</div>
    </div>
  `;
}

function renderDelta(summary) {
  const average = summary.average_agreed_vs_listed_delta;
  const total = summary.total_agreed_vs_listed_delta;

  let tone = "pending";
  let label = "At listed rates overall";

  if (total > 0) {
    tone = "negative";
    label = "Paying above listed rates overall";
  } else if (total < 0) {
    tone = "positive";
    label = "Closing below listed rates overall";
  }

  elements.deltaSummary.innerHTML = `
    <p class="delta-value tone-${tone}">${escapeHtml(formatCurrency(total))}</p>
    <span class="delta-chip ${tone}">${escapeHtml(label)}</span>
    <p class="delta-copy">Avg per deal: ${escapeHtml(formatCurrency(average))}</p>
  `;
}

function renderCalls(recentCalls) {
  if (!recentCalls || recentCalls.length === 0) {
    elements.callsTableBody.innerHTML = `
      <tr>
        <td class="empty-state" colspan="7">No calls have been recorded yet. Complete a carrier flow to populate this table.</td>
      </tr>
    `;
    return;
  }

  elements.callsTableBody.innerHTML = recentCalls
    .map((call, index) => {
      const verificationLabel =
        call.verification_passed === null ? "Pending" : call.verification_passed ? "Verified" : "Failed";
      const rate = call.agreed_rate === null ? "N/A" : formatCurrency(call.agreed_rate);
      const loadSummary = call.selected_load
        ? `${call.selected_load.load_id} · ${call.selected_load.origin} to ${call.selected_load.destination}`
        : "No load selected";
      const detailRowId = `detail-row-${index}`;
      const detailButtonId = `detail-button-${index}`;

      const dealClass = call.agreed_rate !== null ? " call-row--deal" : "";
      const verificationMuted = call.verification_passed === null ? " muted" : "";
      const outcomeMuted = !call.outcome || call.outcome === "unknown" ? " muted" : "";
      const sentimentMuted = !call.sentiment || call.sentiment === "unknown" ? " muted" : "";

      return `
        <tr class="call-row${dealClass}" aria-expanded="false" data-detail="${detailRowId}" role="button" tabindex="0">
          <td>
            <div class="call-identity">
              <span class="call-id">${escapeHtml(call.external_call_id)}</span>
              <span class="call-subtext">${escapeHtml(`${call.mc_number || "No MC"} · ${call.negotiation_rounds} negotiation rounds`)}</span>
            </div>
          </td>
          <td><span class="pill ${call.verification_tone}${verificationMuted}">${verificationLabel}</span></td>
          <td><span class="pill ${call.outcome_tone}${outcomeMuted}">${escapeHtml(sentenceCase(call.outcome))}</span></td>
          <td><span class="pill ${call.sentiment_tone}${sentimentMuted}">${escapeHtml(sentenceCase(call.sentiment))}</span></td>
          <td>${escapeHtml(rate)}</td>
          <td>${escapeHtml(loadSummary)}</td>
          <td>${escapeHtml(formatDateTime(call.ended_at || call.started_at))}</td>
        </tr>
        <tr id="${detailRowId}" class="detail-row" hidden>
          <td class="detail-cell" colspan="7">
            <div class="detail-card">
              <section class="detail-block">
                <h3>Transcript excerpt</h3>
                <p>${escapeHtml(call.transcript_excerpt || "No transcript excerpt captured for this session.")}</p>
              </section>
              <section class="detail-block">
                <h3>Load snapshot</h3>
                ${call.selected_load
          ? `
                      <dl class="detail-grid">
                        <div>
                          <dt>Load ID</dt>
                          <dd>${escapeHtml(call.selected_load.load_id)}</dd>
                        </div>
                        <div>
                          <dt>Equipment</dt>
                          <dd>${escapeHtml(call.selected_load.equipment_type)}</dd>
                        </div>
                        <div>
                          <dt>Route</dt>
                          <dd>${escapeHtml(`${call.selected_load.origin} to ${call.selected_load.destination}`)}</dd>
                        </div>
                        <div>
                          <dt>Listed rate</dt>
                          <dd>${escapeHtml(formatCurrency(call.selected_load.loadboard_rate))}</dd>
                        </div>
                        <div>
                          <dt>Status</dt>
                          <dd>${escapeHtml(sentenceCase(call.selected_load.status))}</dd>
                        </div>
                        <div>
                          <dt>Matched loads</dt>
                          <dd>${escapeHtml(formatNumber(call.matched_loads_count))}</dd>
                        </div>
                      </dl>
                    `
          : '<p class="muted-text">This call did not end with a selected load.</p>'
        }
              </section>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");

  elements.callsTableBody.querySelectorAll(".call-row").forEach((row) => {
    function toggle() {
      const detailRow = document.getElementById(row.dataset.detail);
      const isExpanded = row.getAttribute("aria-expanded") === "true";
      row.setAttribute("aria-expanded", String(!isExpanded));
      detailRow.hidden = isExpanded;
    }

    row.addEventListener("click", toggle);
    row.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggle();
      }
    });
  });
}

function renderPagination(totalCalls, page, pageSize) {
  const totalPages = Math.max(Math.ceil(totalCalls / pageSize), 1);

  const isFirst = page === 0;
  const isLast = page >= totalPages - 1;

  elements.pagination.innerHTML = `
    <button class="pagination-button" data-page="prev" ${isFirst ? "disabled" : ""}>Prev</button>
    <p class="pagination-label">Page ${page + 1} of ${totalPages}</p>
    <button class="pagination-button" data-page="next" ${isLast ? "disabled" : ""}>Next</button>
  `;

  elements.pagination.querySelector('[data-page="prev"]').addEventListener("click", () => {
    if (state.page > 0) {
      state.page--;
      fetchDashboardData({ manual: true });
    }
  });

  elements.pagination.querySelector('[data-page="next"]').addEventListener("click", () => {
    if (state.page < totalPages - 1) {
      state.page++;
      fetchDashboardData({ manual: true });
    }
  });
}

function renderDashboard(data) {
  renderKpis(data.summary);
  renderBars(elements.outcomeChart, data.outcome_breakdown);
  renderBars(elements.sentimentChart, data.sentiment_breakdown);
  renderPie(elements.loadStatusChart, data.load_status_breakdown);
  renderDelta(data.summary);
  renderCalls(data.recent_calls);
  renderPagination(data.total_calls, state.page, state.pageSize);

  elements.lastUpdated.textContent = formatDateTime(data.last_updated_at);
  elements.fetchStatus.textContent = "Live";
}

async function fetchDashboardData({ manual = false } = {}) {
  if (state.isFetching) {
    return;
  }

  state.isFetching = true;
  elements.refreshButton.disabled = true;
  elements.fetchStatus.textContent = "Refreshing...";

  try {
    const offset = state.page * state.pageSize;
    const response = await fetch(`/dashboard/data?limit=${state.pageSize}&offset=${offset}`, {
      headers: {
        Accept: "application/json",
      },
    });

    if (response.status === 401) {
      window.location.assign("/dashboard");
      return;
    }

    if (!response.ok) {
      throw new Error(`Dashboard request failed with status ${response.status}`);
    }

    const data = await response.json();
    state.data = data;
    renderDashboard(data);
    elements.staleWarning.hidden = true;
    elements.staleWarning.textContent = "";
  } catch (error) {
    console.error(error);
    elements.fetchStatus.textContent = "Offline";

    if (state.data) {
      elements.staleWarning.hidden = false;
      elements.staleWarning.textContent = "Latest refresh failed. The dashboard is still showing the most recent successful data.";
    } else {
      elements.staleWarning.hidden = false;
      elements.staleWarning.textContent = "Unable to load dashboard data yet. Check the API and try again.";
    }
  } finally {
    state.isFetching = false;
    elements.refreshButton.disabled = false;
  }
}

function startAutoRefresh() {
  if (state.timerId !== null) {
    clearInterval(state.timerId);
  }

  state.timerId = window.setInterval(() => {
    fetchDashboardData();
  }, REFRESH_INTERVAL_MS);
}

elements.refreshButton.addEventListener("click", () => {
  fetchDashboardData({ manual: true });
});

fetchDashboardData();
startAutoRefresh();
