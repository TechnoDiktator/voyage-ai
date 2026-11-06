// Thread of the run currently waiting for human approval (or just finished).
let currentThreadId = null;
let latestAnswerMarkdown = "";

const SPECIALISTS = [
    { id: "flight_agent", label: "Flights" },
    { id: "hotel_agent", label: "Hotels" },
    { id: "weather_agent", label: "Weather" },
    { id: "budget_agent", label: "Budget" }
];

const AGENT_OUTPUT_FIELDS = [
    { key: "flight_results", label: "Flight agent" },
    { key: "hotel_results", label: "Hotel agent" },
    { key: "weather_results", label: "Weather agent" },
    { key: "budget_results", label: "Budget agent" }
];

const $ = (id) => document.getElementById(id);

function setPrompt(text) {
    $("userInput").value = text;
}

function setLoading(isLoading) {
    $("sendBtn").disabled = isLoading;
    $("btnText").classList.toggle("hidden", isLoading);
    $("btnLoader").classList.toggle("hidden", !isLoading);
}

function setApprovalBusy(isBusy) {
    $("approveBtn").disabled = isBusy;
    $("reviseBtn").disabled = isBusy;
    $("feedbackInput").disabled = isBusy;
}

function showError(message) {
    const errorBox = $("errorBox");
    errorBox.textContent = message;
    errorBox.classList.remove("hidden");
}

function hideError() {
    const errorBox = $("errorBox");
    errorBox.classList.add("hidden");
    errorBox.textContent = "";
}

function renderMarkdown(target, markdown) {
    if (typeof marked !== "undefined") {
        target.innerHTML = marked.parse(markdown || "");
    } else {
        target.innerText = markdown || "";
    }
}

/* ---------- Pipeline ---------- */

// Builds the list of workflow steps and their states from the API response.
function buildSteps(data) {
    const blocked = data.guardrail_allowed === false;
    const paused = Boolean(data.requires_approval);
    const selected = data.selected_agents || [];

    if (blocked) {
        return [
            { label: "Guardrail", state: "blocked", note: "Blocked" },
            { label: "Supervisor", state: "idle" },
            { label: "Specialists", state: "idle" },
            { label: "Itinerary", state: "idle" },
            { label: "Human review", state: "idle" },
            { label: "Final plan", state: "idle" }
        ];
    }

    const steps = [
        { label: "Guardrail", state: "done", note: "Passed" },
        { label: "Supervisor", state: "done", note: "Routed" }
    ];

    SPECIALISTS.forEach((agent) => {
        const used = selected.includes(agent.id);
        steps.push({
            label: agent.label,
            state: used ? "done" : "skipped",
            note: used ? "Ran" : "Skipped"
        });
    });

    steps.push({ label: "Itinerary", state: "done", note: "Drafted" });

    if (paused) {
        const round = data.revision_count
            ? `Waiting for you (revision ${data.revision_count} of ${data.max_revisions})`
            : "Waiting for you";
        steps.push({ label: "Human review", state: "active", note: round });
        steps.push({ label: "Final plan", state: "idle" });
    } else {
        const revised = data.approved === false;
        steps.push({
            label: "Human review",
            state: "done",
            note: revised ? "Revision requested" : "Approved"
        });
        steps.push({ label: "Final plan", state: "done", note: "Ready" });
    }

    return steps;
}

function renderPipeline(steps) {
    const list = $("pipeline");
    list.innerHTML = "";

    steps.forEach((step) => {
        const item = document.createElement("li");
        item.className = `step step-${step.state}`;

        const name = document.createElement("span");
        name.className = "step-name";
        name.textContent = step.label;
        item.appendChild(name);

        if (step.note) {
            const note = document.createElement("span");
            note.className = "step-note";
            note.textContent = step.note;
            item.appendChild(note);
        }

        list.appendChild(item);
    });
}

function renderSupervisor(data) {
    const box = $("supervisorBox");
    const constraints = data.trip_constraints || {};
    const chips = $("constraintChips");
    chips.innerHTML = "";

    const labels = {
        destination: "Destination",
        origin: "From",
        duration: "Duration",
        budget: "Budget",
        travel_style: "Style"
    };

    Object.entries(labels).forEach(([key, label]) => {
        if (constraints[key]) {
            addChip(chips, `${label}: ${constraints[key]}`);
        }
    });

    (constraints.special_preferences || []).forEach((pref) => addChip(chips, pref));

    const hasContent = data.supervisor_reasoning || chips.children.length;

    $("supervisorReasoning").textContent = data.supervisor_reasoning || "";
    box.classList.toggle("hidden", !hasContent || data.guardrail_allowed === false);
}

function addChip(container, text) {
    const chip = document.createElement("span");
    chip.className = "constraint-chip";
    chip.textContent = text;
    container.appendChild(chip);
}

function renderAgentOutputs(data) {
    const container = $("agentOutputs");
    container.querySelectorAll("details").forEach((node) => node.remove());

    let count = 0;

    AGENT_OUTPUT_FIELDS.forEach((field) => {
        const value = data[field.key];
        if (!value || !String(value).trim()) {
            return;
        }

        const details = document.createElement("details");
        const summary = document.createElement("summary");
        const body = document.createElement("pre");

        summary.textContent = field.label;
        body.textContent = typeof value === "string"
            ? value.trim()
            : JSON.stringify(value, null, 2);

        details.appendChild(summary);
        details.appendChild(body);
        container.appendChild(details);
        count += 1;
    });

    container.classList.toggle("hidden", count === 0);
}

/* ---------- Result rendering ---------- */

function setStatusBadge(text, kind) {
    const badge = $("statusBadge");
    badge.textContent = text;
    badge.className = `status-badge badge-${kind}`;
}

// Renders any API response: blocked, awaiting approval, or final.
function showResult(data) {
    const blocked = data.guardrail_allowed === false;
    const paused = Boolean(data.requires_approval);

    latestAnswerMarkdown = data.answer || "";
    currentThreadId = data.thread_id;

    renderMarkdown($("resultBox"), latestAnswerMarkdown);
    $("threadInfo").textContent = `Thread ID: ${data.thread_id}`;

    renderPipeline(buildSteps(data));
    renderSupervisor(data);
    renderAgentOutputs(data);

    $("guardrailBanner").classList.toggle("hidden", !blocked);
    $("guardrailReason").textContent = blocked
        ? (data.guardrail_reason || data.answer || "This request is outside what the travel planner can help with.")
        : "";

    $("approvalPanel").classList.toggle("hidden", !paused);
    if (paused) {
        $("approveBtn").textContent = "Approve and finalize";
        $("approvalRequest").textContent =
            data.approval_request ||
            "Approve the draft below, or request changes and the final plan will apply your feedback.";
        $("feedbackInput").value = "";
    }
    setApprovalBusy(false);

    // The blocked message is already shown in the banner.
    $("pdfContent").classList.toggle("hidden", blocked);

    const canExport = !blocked && !paused;
    $("copyBtn").classList.toggle("hidden", blocked);
    $("downloadBtn").classList.toggle("hidden", !canExport);

    if (blocked) {
        $("resultTitle").textContent = "Request not processed";
        setStatusBadge("Blocked", "blocked");
    } else if (paused) {
        $("resultTitle").textContent = data.revision_count
            ? `Revised draft ${data.revision_count} - your review needed`
            : "Draft itinerary - your review needed";
        setStatusBadge("Awaiting approval", "pending");
        $("reviseBtn").textContent = data.revision_count >= data.max_revisions - 1
            ? "Request final revision"
            : "Request revision";
    } else {
        $("resultTitle").textContent = "Your AI Travel Plan";
        setStatusBadge(data.approved === false ? "Revised" : "Approved", "approved");
    }

    const resultSection = $("resultSection");
    resultSection.classList.remove("hidden");
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function postJson(url, payload) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
        throw new Error(data.error || "Something went wrong.");
    }

    return data;
}

/* ---------- Actions ---------- */

async function sendMessage() {
    hideError();

    const message = $("userInput").value.trim();

    if (!message) {
        showError("Please enter your travel request first.");
        return;
    }

    setLoading(true);

    try {
        // Each request starts a fresh thread so it never collides with a run paused for approval.
        const data = await postJson("/api/travel", { message: message });
        showResult(data);
    } catch (error) {
        showError(error.message);
    } finally {
        setLoading(false);
    }
}

async function submitApproval(approved) {
    hideError();

    const feedback = $("feedbackInput").value.trim();

    if (!approved && !feedback) {
        showError("Please describe what to change before requesting a revision.");
        $("feedbackInput").focus();
        return;
    }

    if (!currentThreadId) {
        showError("No plan is waiting for approval.");
        return;
    }

    setApprovalBusy(true);
    const activeBtn = approved ? $("approveBtn") : $("reviseBtn");
    const oldText = activeBtn.textContent;
    activeBtn.textContent = approved ? "Finalizing..." : "Revising...";

    try {
        const data = await postJson("/api/travel/approve", {
            thread_id: currentThreadId,
            approved: approved,
            feedback: feedback
        });
        showResult(data);
    } catch (error) {
        showError(error.message);
        setApprovalBusy(false);
        activeBtn.textContent = oldText;
    }
}

function startNewPlan() {
    currentThreadId = null;
    latestAnswerMarkdown = "";
    hideError();

    $("resultSection").classList.add("hidden");
    $("userInput").value = "";
    $("userInput").focus();
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function copyResult() {
    const text = $("resultBox").innerText;

    if (!text) {
        return;
    }

    navigator.clipboard.writeText(text)
        .then(() => {
            const copyBtn = $("copyBtn");
            const oldText = copyBtn.textContent;

            copyBtn.textContent = "Copied!";

            setTimeout(() => {
                copyBtn.textContent = oldText;
            }, 1400);
        })
        .catch(() => {
            showError("Could not copy result.");
        });
}

function downloadPDF() {
    const pdfContent = $("pdfContent");

    if (!latestAnswerMarkdown || !pdfContent) {
        showError("No travel plan available to download.");
        return;
    }

    const downloadBtn = $("downloadBtn");
    const oldText = downloadBtn.textContent;

    downloadBtn.textContent = "Preparing PDF...";
    downloadBtn.disabled = true;

    const options = {
        margin: 0.5,
        filename: "ai-travel-plan.pdf",
        image: {
            type: "jpeg",
            quality: 0.98
        },
        html2canvas: {
            scale: 2,
            useCORS: true,
            backgroundColor: "#ffffff"
        },
        jsPDF: {
            unit: "in",
            format: "a4",
            orientation: "portrait"
        },
        pagebreak: {
            mode: ["avoid-all", "css", "legacy"]
        }
    };

    html2pdf()
        .set(options)
        .from(pdfContent)
        .save()
        .then(() => {
            downloadBtn.textContent = oldText;
            downloadBtn.disabled = false;
        })
        .catch(() => {
            downloadBtn.textContent = oldText;
            downloadBtn.disabled = false;
            showError("Could not download PDF.");
        });
}

document.addEventListener("keydown", function (event) {
    if (event.ctrlKey && event.key === "Enter" && document.activeElement === $("userInput")) {
        sendMessage();
    }
});
