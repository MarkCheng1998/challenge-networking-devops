/**
 * Cisco交换机VLAN配置自动化 - 前端交互脚本
 */

// 初始化页面
function initPage() {
    // 加载默认VLAN
    DEFAULT_VLANS.forEach(vlan => addVlanRow(vlan.id, vlan.name));
}

// 添加VLAN行
function addVlanRow(id = "", name = "") {
    const vlanList = document.getElementById("vlan-list");
    const row = document.createElement("div");
    row.className = "vlan-row";
    row.innerHTML = `
        <input type="number" class="vlan-id" value="${id}" placeholder="VLAN ID" min="1" max="4094">
        <input type="text" class="vlan-name" value="${name}" placeholder="VLAN名称">
        <button type="button" class="btn-remove" onclick="removeVlanRow(this)">&times;</button>
    `;
    vlanList.appendChild(row);
}

// 移除VLAN行
function removeVlanRow(btn) {
    btn.parentElement.remove();
}

// 收集表单数据
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

// 显示加载状态
function showLoading() {
    document.getElementById("result-content").innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>正在执行配置，请稍候...</p>
        </div>
    `;
}

// 执行完整自动化配置
async function applyConfiguration() {
    const data = collectFormData();

    if (data.vlans.length === 0) {
        alert("请至少添加一个VLAN");
        return;
    }
    if (!data.hostname) {
        alert("请输入交换机主机名");
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
        renderError("请求失败: " + error.message);
    }
}

// 仅验证配置
async function validateOnly() {
    const data = collectFormData();

    if (data.vlans.length === 0) {
        alert("请至少添加一个VLAN");
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
        renderError("请求失败: " + error.message);
    }
}

// 渲染完整配置结果
function renderResult(result) {
    let html = "";

    // 总体状态
    if (result.success) {
        html += `<div class="alert alert-success">✓ 自动化配置流程执行成功！</div>`;
    } else {
        html += `<div class="alert alert-danger">✗ 配置过程中出现错误，请查看下方详情。</div>`;
    }

    // 连接状态
    html += renderStepCard("交换机连接", result.connection, result.connection ? "连接成功" : "连接失败");

    // VLAN配置
    if (result.vlan_config) {
        html += renderStepCard("VLAN配置", result.vlan_config.success, result.vlan_config.details.join("\n"));
    }

    // 主机名配置
    if (result.hostname_config) {
        html += renderStepCard("主机名修改", result.hostname_config.success, result.hostname_config.details.join("\n"));
    }

    // 保存配置
    if (result.save) {
        html += renderStepCard("保存到NVRAM", result.save.success, result.save.details.join("\n"));
    }

    // 配置备份
    if (result.backup) {
        const backupText = result.backup.details.join("\n") + (result.backup.file_path ? `\n备份文件: ${result.backup.file_path}` : "");
        html += renderStepCard("配置备份", result.backup.success, backupText);
    }

    // 配置验证
    if (result.validation) {
        html += renderValidationSection(result.validation);
    }

    // 错误汇总
    if (result.errors && result.errors.length > 0) {
        html += `<div class="result-card error">
            <h4>⚠ 错误汇总</h4>
            <div>${result.errors.map(e => `<div class="alert alert-danger">${e}</div>`).join("")}</div>
        </div>`;
    }

    document.getElementById("result-content").innerHTML = html;
}

// 渲染单个步骤卡片
function renderStepCard(title, success, details) {
    const status = success ? "✓" : "✗";
    const cardClass = success ? "success" : "error";
    return `<div class="result-card ${cardClass}">
        <h4>${status} ${title}</h4>
        <pre>${details || "无详细信息"}</pre>
    </div>`;
}

// 渲染验证结果区域
function renderValidationSection(validation) {
    let html = `<div class="result-card ${validation.is_valid ? "success" : "error"}">
        <h4>${validation.is_valid ? "✓" : "⚠"} 配置验证</h4>`;

    // 告警信息
    if (validation.alerts && validation.alerts.length > 0) {
        validation.alerts.forEach(alert => {
            let alertClass = "alert-info";
            if (alert.includes("✓")) alertClass = "alert-success";
            else if (alert.includes("⚠")) alertClass = "alert-warning";
            else if (alert.includes("ℹ")) alertClass = "alert-info";
            html += `<div class="alert ${alertClass}">${alert}</div>`;
        });
    }

    // VLAN匹配表格
    if (validation.vlan_matches && validation.vlan_matches.length > 0) {
        html += `<table class="vlan-table">
            <tr><th>VLAN ID</th><th>名称</th><th>状态</th></tr>`;
        validation.vlan_matches.forEach(v => {
            html += `<tr><td>${v.id}</td><td>${v.name}</td><td class="status-ok">${v.status}</td></tr>`;
        });
        html += `</table>`;
    }

    // VLAN不匹配表格
    if (validation.vlan_mismatches && validation.vlan_mismatches.length > 0) {
        html += `<table class="vlan-table">
            <tr><th>VLAN ID</th><th>问题</th><th>期望名称</th><th>实际名称</th></tr>`;
        validation.vlan_mismatches.forEach(v => {
            html += `<tr><td>${v.id}</td><td>${v.issue}</td><td>${v.expected_name}</td><td>${v.actual_name || "-"}</td></tr>`;
        });
        html += `</table>`;
    }

    // 额外VLAN
    if (validation.extra_vlans && validation.extra_vlans.length > 0) {
        html += `<table class="vlan-table">
            <tr><th>非标准VLAN ID</th><th>名称</th></tr>`;
        validation.extra_vlans.forEach(v => {
            html += `<tr><td>${v.id}</td><td>${v.name}</td></tr>`;
        });
        html += `</table>`;
    }

    html += `</div>`;
    return html;
}

// 渲染仅验证结果
function renderValidationResult(validation) {
    document.getElementById("result-content").innerHTML = renderValidationSection(validation);
}

// 渲染错误
function renderError(message) {
    document.getElementById("result-content").innerHTML = `
        <div class="alert alert-danger">${message}</div>
    `;
}
