/**
 * Cisco Switch VLAN Configuration Automation - Frontend Interaction Script
 */

// Initialize page
function initPage() {
    // Load default VLANs
    DEFAULT_VLANS.forEach(vlan => addVlanRow(vlan.id, vlan.name));
}

// Add VLAN row
function addVlanRow(id = "", name = "") {
    const vlanList = document.getElementById("vlan-list");
    const row = document.createElement("div");
    row.className = "vlan-row";
    row.innerHTML = `
        <input type="number" class="vlan-id" value="${id}" placeholder="VLAN ID" min="1" max="4094">
        <input type="text" class="vlan-name" value="${name}" placeholder="VLAN Name">
        <button type="button" class="btn-remove" onclick="removeVlanRow(this)">&times;</button>
    `;
    vlanList.appendChild(row);
}

// Remove VLAN row
function removeVlanRow(btn) {
    btn.parentElement.remove();
}

// Collect form data
function collectFormData() {
    const vlanRows = document.querySelectorAll(".vlan-row");
    const vlans = [];
    vlanRows.forEach(row => {
        const id = row.querySelector(".vlan-id").value.trim();
        const name = row.querySelector(".vlan-name").value.trim();
        if (id && name) {
            vlans.push({ id: id, name: name });
        }
    });

    return {
        host: document.getElementById("host").value.trim(),
        username: document.getElementById("username").value.trim(),
        password: document.getElementById("password").value.trim(),
        port: document.getElementById("port").value.trim() || "22",
        enable_password: document.getElementById("enable_password").value.trim(),
        hostname: document.getElementById("hostname").value.trim(),
        vlans: vlans,
        simulate: document.getElementById("simulate").checked,
    };
}

// Show loading state
function showLoading() {
    document.getElementById("result-content").innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Executing configuration, please wait...</p>
        </div>
    `;
}

// Execute full automated configuration
async function applyConfiguration() {
    const data = collectFormData();

    if (data.vlans.length === 0) {
        alert("Please add at least one VLAN");
        return;
    }
    if (!data.hostname) {
        alert("Please enter the switch hostname");
        return;
    }

    showLoading();

    try {
        const response = await fetch("/api/configure", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
        const result = await response.json();
        renderResult(result);
    } catch (error) {
        renderError("Request failed: " + error.message);
    }
}

// Validate configuration only
async function validateOnly() {
    const data = collectFormData();

    if (data.vlans.length === 0) {
        alert("Please add at least one VLAN");
        return;
    }

    showLoading();

    const payload = {
        ...data,
        expected_vlans: data.vlans,
        expected_hostname: data.hostname,
    };

    try {
        const response = await fetch("/api/validate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const result = await response.json();
        renderValidationResult(result);
    } catch (error) {
        renderError("Request failed: " + error.message);
    }
}

// Render full configuration result
function renderResult(result) {
    let html = "";

    // Overall status
    if (result.success) {
        html += `<div class="alert alert-success">OK: Automated configuration workflow completed successfully!</div>`;
    } else {
        html += `<div class="alert alert-danger">FAIL: Errors occurred during configuration. See details below.</div>`;
    }

    // Connection status
    html += renderStepCard("Switch Connection", result.connection, result.connection ? "Connected" : "Connection failed");

    // VLAN configuration
    if (result.vlan_config) {
        html += renderStepCard("VLAN Configuration", result.vlan_config.success, result.vlan_config.details.join("\n"));
    }

    // Hostname configuration
    if (result.hostname_config) {
        html += renderStepCard("Hostname Modification", result.hostname_config.success, result.hostname_config.details.join("\n"));
    }

    // Save configuration
    if (result.save) {
        html += renderStepCard("Save to NVRAM", result.save.success, result.save.details.join("\n"));
    }

    // Configuration backup
    if (result.backup) {
        const backupText = result.backup.details.join("\n") + (result.backup.file_path ? `\nBackup file: ${result.backup.file_path}` : "");
        html += renderStepCard("Configuration Backup", result.backup.success, backupText);
    }

    // Configuration validation
    if (result.validation) {
        html += renderValidationSection(result.validation);
    }

    // Error summary
    if (result.errors && result.errors.length > 0) {
        html += `<div class="result-card error">
            <h4>WARNING: Error Summary</h4>
            <div>${result.errors.map(e => `<div class="alert alert-danger">${e}</div>`).join("")}</div>
        </div>`;
    }

    document.getElementById("result-content").innerHTML = html;
}

// Render a single step card
function renderStepCard(title, success, details) {
    const status = success ? "OK" : "FAIL";
    const cardClass = success ? "success" : "error";
    return `<div class="result-card ${cardClass}">
        <h4>${status} ${title}</h4>
        <pre>${details || "No details available"}</pre>
    </div>`;
}

// Render validation result section
function renderValidationSection(validation) {
    let html = `<div class="result-card ${validation.is_valid ? "success" : "error"}">
        <h4>${validation.is_valid ? "OK" : "WARNING"} Configuration Validation</h4>`;

    // Alert messages
    if (validation.alerts && validation.alerts.length > 0) {
        validation.alerts.forEach(alert => {
            let alertClass = "alert-info";
            if (alert.includes("OK")) alertClass = "alert-success";
            else if (alert.includes("WARNING")) alertClass = "alert-warning";
            else if (alert.includes("INFO")) alertClass = "alert-info";
            html += `<div class="alert ${alertClass}">${alert}</div>`;
        });
    }

    // VLAN match table
    if (validation.vlan_matches && validation.vlan_matches.length > 0) {
        html += `<table class="vlan-table">
            <tr><th>VLAN ID</th><th>Name</th><th>Status</th></tr>`;
        validation.vlan_matches.forEach(v => {
            html += `<tr><td>${v.id}</td><td>${v.name}</td><td class="status-ok">${v.status}</td></tr>`;
        });
        html += `</table>`;
    }

    // VLAN mismatch table
    if (validation.vlan_mismatches && validation.vlan_mismatches.length > 0) {
        html += `<table class="vlan-table">
            <tr><th>VLAN ID</th><th>Issue</th><th>Expected Name</th><th>Actual Name</th></tr>`;
        validation.vlan_mismatches.forEach(v => {
            html += `<tr><td>${v.id}</td><td>${v.issue}</td><td>${v.expected_name}</td><td>${v.actual_name || "-"}</td></tr>`;
        });
        html += `</table>`;
    }

    // Extra VLANs
    if (validation.extra_vlans && validation.extra_vlans.length > 0) {
        html += `<table class="vlan-table">
            <tr><th>Non-standard VLAN ID</th><th>Name</th></tr>`;
        validation.extra_vlans.forEach(v => {
            html += `<tr><td>${v.id}</td><td>${v.name}</td></tr>`;
        });
        html += `</table>`;
    }

    html += `</div>`;
    return html;
}

// Render validation-only result
function renderValidationResult(validation) {
    document.getElementById("result-content").innerHTML = renderValidationSection(validation);
}

// Render error
function renderError(message) {
    document.getElementById("result-content").innerHTML = `
        <div class="alert alert-danger">${message}</div>
    `;
}
