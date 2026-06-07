/**
 * Dashboard - Statistics, Charts, and Date Search
 * Fab Stream Business Platform
 */

// Global chart references for cleanup
let performanceChart = null;
let attendanceChart = null;
let taskChart = null;
let deptChart = null;

// Color palette
const COLORS = {
    primary: '#0f766e',
    primaryLight: '#14b8a6',
    success: '#22c55e',
    warning: '#f59e0b',
    danger: '#ef4444',
    info: '#3b82f6',
    purple: '#8b5cf6',
    gray: '#94a3b8',
    ink: '#172033',
    muted: '#64748b',
    line: '#e2e8f0'
};

document.addEventListener('DOMContentLoaded', () => {
    // Set today's date in the date picker
    const dateInput = document.getElementById('dateSearch');
    if (dateInput) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.value = today;
        dateInput.max = today;
    }

    // Initial load
    refreshDashboard();
});

/**
 * Fetch dashboard stats and update everything
 */
function refreshDashboard() {
    fetch('/api/dashboard/stats')
        .then(res => res.json())
        .then(data => {
            updateTopStats(data);
            updateAttendanceTable(data.attendance_list);
            updateTodayStats(data.today);
            updateActivityFeed(data.recent_activity);
            updateCharts(data);
            animateCounters();
        })
        .catch(err => console.error('Dashboard data error:', err));
}

/**
 * Animate counter numbers
 */
function animateCounters() {
    const counters = document.querySelectorAll('.dash-stat-value');
    counters.forEach(counter => {
        const target = parseInt(counter.dataset.count || counter.textContent || '0');
        if (target === 0) return;
        const duration = 1000;
        const start = performance.now();
        const tick = (now) => {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            counter.textContent = Math.round(target * eased);
            if (progress < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
    });
}

/**
 * Update top stat cards
 */
function updateTopStats(data) {
    const t = data.today;

    setText('stat-employees', t.total_employees);
    setText('stat-present', t.present);
    setText('stat-late', t.late);
    setText('stat-absent', t.absent);
    setText('stat-performance', t.daily_stat.performance_score + '%');
    setText('stat-tasks-done', t.done_tasks);

    // Update card data attributes for counter animation
    setDataCount('card-present', t.present);
    setDataCount('card-late', t.late);
    setDataCount('card-absent', t.absent);
    setDataCount('card-performance', t.daily_stat.performance_score);
    setDataCount('card-tasks', t.done_tasks);

    // Attendance badge
    const badge = document.getElementById('attendanceCountBadge');
    if (badge) {
        badge.textContent = t.present + ' checked in';
        badge.className = t.present > 0 ? 'badge bg-success' : 'badge bg-secondary';
    }

    // Today's date badge
    const dateBadge = document.getElementById('todayDateBadge');
    if (dateBadge) {
        const d = new Date();
        dateBadge.textContent = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
}

/**
 * Update today's attendance table
 */
function updateAttendanceTable(attendanceList) {
    const tbody = document.getElementById('attendanceTableBody');
    if (!tbody) return;

    if (!attendanceList || attendanceList.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-3">No one checked in yet today.</td></tr>';
        return;
    }

    tbody.innerHTML = attendanceList.map(a => {
        const statusClass = a.status === 'present' ? 'status-present' : a.status === 'late' ? 'status-late' : 'status-half';
        const statusLabel = a.status.charAt(0).toUpperCase() + a.status.slice(1);
        return `<tr>
            <td><strong>${escapeHtml(a.full_name)}</strong><br><small class="text-muted">${escapeHtml(a.position)}</small></td>
            <td>${escapeHtml(a.department)}</td>
            <td>${a.check_in}</td>
            <td><span class="status-dot ${statusClass}"></span> ${statusLabel}</td>
        </tr>`;
    }).join('');
}

/**
 * Update today's statistics detail grid
 */
function updateTodayStats(today) {
    const ds = today.daily_stat;
    setText('detail-reports', ds.reports_sent);
    setText('detail-chat', ds.chat_messages);
    setText('detail-messages', ds.messages_sent);
    setText('detail-updates', ds.updates_published);
    setText('detail-tasks-created', ds.tasks_created);
    setText('detail-tasks-completed', ds.tasks_completed);
}

/**
 * Update the recent activity feed
 */
function updateActivityFeed(activities) {
    const feed = document.getElementById('activityFeed');
    if (!feed) return;

    if (!activities || activities.length === 0) {
        feed.innerHTML = '<div class="text-center text-muted py-3">No recent activity.</div>';
        return;
    }

    const icons = {
        report: '📄',
        update: '📢',
        task: '📋',
        chat: '💬',
        message: '✉️'
    };

    feed.innerHTML = activities.map(a => `
        <div class="activity-feed-item activity-${a.type}">
            <div class="activity-icon">${icons[a.type] || '📌'}</div>
            <div class="activity-content">
                <strong>${escapeHtml(a.title)}</strong>
                <p>${escapeHtml(a.description)}</p>
                <small>${a.date_str}</small>
            </div>
        </div>
    `).join('');
}

/**
 * Initialize / Update all charts
 */
function updateCharts(data) {
    // Performance trend chart
    const perfCtx = document.getElementById('performanceChart');
    if (perfCtx) {
        if (performanceChart) performanceChart.destroy();
        const labels = data.last_7_days.map(d => d.date_label);
        const scores = data.last_7_days.map(d => d.performance_score);

        performanceChart = new Chart(perfCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Performance Score',
                    data: scores,
                    borderColor: COLORS.primary,
                    backgroundColor: 'rgba(15, 118, 110, 0.08)',
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: COLORS.primary,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    borderWidth: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: ctx => 'Score: ' + ctx.parsed.y + '%'
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: 'rgba(0,0,0,0.04)' },
                        ticks: { callback: v => v + '%' }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    // Attendance chart
    const attCtx = document.getElementById('attendanceChart');
    if (attCtx) {
        if (attendanceChart) attendanceChart.destroy();
        const labels = data.last_7_days.map(d => d.date_label);
        const present = data.last_7_days.map(d => d.present_count);
        const absent = data.last_7_days.map(d => Math.max(0, data.today.total_employees - d.present_count));

        attendanceChart = new Chart(attCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Present',
                        data: present,
                        backgroundColor: COLORS.success,
                        borderRadius: 4,
                        barPercentage: 0.6
                    },
                    {
                        label: 'Absent',
                        data: absent,
                        backgroundColor: COLORS.danger,
                        borderRadius: 4,
                        barPercentage: 0.6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { usePointStyle: true, padding: 12 }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.04)' },
                        stacked: false
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    // Task status chart (doughnut)
    const taskCtx = document.getElementById('taskChart');
    if (taskCtx) {
        if (taskChart) taskChart.destroy();
        taskChart = new Chart(taskCtx, {
            type: 'doughnut',
            data: {
                labels: ['To Do', 'In Progress', 'Done'],
                datasets: [{
                    data: [
                        data.today.todo_tasks,
                        data.today.in_progress_tasks,
                        data.today.done_tasks
                    ],
                    backgroundColor: [COLORS.warning, COLORS.info, COLORS.success],
                    borderWidth: 0,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { usePointStyle: true, padding: 12 }
                    }
                },
                cutout: '65%'
            }
        });
    }

    // Department distribution chart
    const deptCtx = document.getElementById('deptChart');
    if (deptCtx) {
        if (deptChart) deptChart.destroy();
        const deptColors = [COLORS.primary, COLORS.info, COLORS.purple, COLORS.warning, COLORS.danger, COLORS.success];
        const deptData = data.department_distribution;

        deptChart = new Chart(deptCtx, {
            type: 'doughnut',
            data: {
                labels: deptData.map(d => d.name),
                datasets: [{
                    data: deptData.map(d => d.employees),
                    backgroundColor: deptData.map((_, i) => deptColors[i % deptColors.length]),
                    borderWidth: 0,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { usePointStyle: true, padding: 12 }
                    }
                },
                cutout: '65%'
            }
        });
    }
}

/**
 * Search statistics by date
 */
function searchDateStats() {
    const dateInput = document.getElementById('dateSearch');
    const dateValue = dateInput ? dateInput.value : '';

    if (!dateValue) {
        alert('Please select a date to search.');
        return;
    }

    const panel = document.getElementById('dateStatsPanel');
    const display = document.getElementById('dashDateDisplay');
    const subtitle = document.getElementById('dashDateSubtitle');

    if (display) display.textContent = 'Searching...';
    if (subtitle) subtitle.textContent = dateValue;

    fetch('/api/dashboard/stats-by-date?date=' + dateValue)
        .then(res => res.json())
        .then(data => {
            // Show the panel
            if (panel) panel.style.display = 'block';

            // Update title
            const titleSpan = document.getElementById('selectedDateLabel');
            if (titleSpan) {
                const d = new Date(data.date + 'T00:00:00');
                titleSpan.textContent = d.toLocaleDateString('en-US', {
                    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
                });
            }

            // Update date display
            if (display) display.textContent = 'Date Search Results';
            if (subtitle) {
                const d = new Date(data.date + 'T00:00:00');
                subtitle.textContent = d.toLocaleDateString('en-US', {
                    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
                });
            }

            // Update stats grid
            updateDateStatsGrid(data);

            // Update attendance table
            populateDateAttendance(data.attendance);

            // Update absent users
            populateDateAbsent(data.absent_users);

            // Update activity log
            populateDateActivityLog(data.activities);

            // Scroll to panel
            if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        })
        .catch(err => {
            console.error('Date search error:', err);
            if (display) display.textContent = 'Error loading data';
        });
}

/**
 * Populate date stats grid
 */
function updateDateStatsGrid(data) {
    const grid = document.getElementById('dateStatsGrid');
    if (!grid) return;

    const s = data.stat;
    grid.innerHTML = `
        <div class="dash-stat-card dash-stat-card-sm dash-stat-card-success">
            <span class="dash-stat-value">${s.present_count}</span>
            <strong>Present</strong>
        </div>
        <div class="dash-stat-card dash-stat-card-sm dash-stat-card-warning">
            <span class="dash-stat-value">${s.late_count}</span>
            <strong>Late</strong>
        </div>
        <div class="dash-stat-card dash-stat-card-sm dash-stat-card-danger">
            <span class="dash-stat-value">${s.absent_count}</span>
            <strong>Absent</strong>
        </div>
        <div class="dash-stat-card dash-stat-card-sm dash-stat-card-info">
            <span class="dash-stat-value">${s.performance_score}%</span>
            <strong>Performance</strong>
        </div>
        <div class="dash-stat-card dash-stat-card-sm dash-stat-card-primary">
            <span class="dash-stat-value">${s.tasks_created}</span>
            <strong>Tasks Created</strong>
        </div>
        <div class="dash-stat-card dash-stat-card-sm dash-stat-card-purple">
            <span class="dash-stat-value">${s.tasks_completed}</span>
            <strong>Tasks Done</strong>
        </div>
        <div class="dash-stat-card dash-stat-card-sm dash-stat-card-success">
            <span class="dash-stat-value">${s.reports_sent}</span>
            <strong>Reports</strong>
        </div>
        <div class="dash-stat-card dash-stat-card-sm dash-stat-card-primary">
            <span class="dash-stat-value">${s.chat_messages}</span>
            <strong>Chat Msgs</strong>
        </div>
        <div class="dash-stat-card dash-stat-card-sm dash-stat-card-warning">
            <span class="dash-stat-value">${s.updates_published}</span>
            <strong>Updates</strong>
        </div>
    `;
}

/**
 * Populate date attendance table
 */
function populateDateAttendance(attendance) {
    const tbody = document.getElementById('dateAttendanceBody');
    if (!tbody) return;

    if (!attendance || attendance.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">No attendance records for this date.</td></tr>';
        return;
    }

    tbody.innerHTML = attendance.map(a => `
        <tr>
            <td><strong>${escapeHtml(a.username)}</strong><br><small class="text-muted">${escapeHtml(a.position)}</small></td>
            <td>${escapeHtml(a.department)}</td>
            <td>${a.check_in}</td>
            <td>${a.check_out}</td>
            <td><span class="status-dot status-${a.status}"></span> ${a.status.charAt(0).toUpperCase() + a.status.slice(1)}</td>
        </tr>
    `).join('');
}

/**
 * Populate date absent table
 */
function populateDateAbsent(absentUsers) {
    const tbody = document.getElementById('dateAbsentBody');
    if (!tbody) return;

    if (!absentUsers || absentUsers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="2" class="text-center text-muted py-3">Everyone was present!</td></tr>';
        return;
    }

    tbody.innerHTML = absentUsers.map(u => `
        <tr>
            <td>${escapeHtml(u.full_name)}</td>
            <td>${escapeHtml(u.department)}</td>
        </tr>
    `).join('');
}

/**
 * Populate date activity log
 */
function populateDateActivityLog(activities) {
    const log = document.getElementById('dateActivityLog');
    if (!log) return;

    if (!activities || activities.length === 0) {
        log.innerHTML = '<div class="text-center text-muted py-3">No activity recorded for this date.</div>';
        return;
    }

    const icons = {
        report: '📄',
        update: '📢',
        task: '📋',
        chat: '💬',
        message: '✉️'
    };

    log.innerHTML = activities.map(a => `
        <div class="activity-feed-item activity-${a.type}">
            <div class="activity-icon">${icons[a.type] || '📌'}</div>
            <div class="activity-content">
                <strong>${escapeHtml(a.title)}</strong>
                <p>${escapeHtml(a.description)}</p>
                <small>${a.time}</small>
            </div>
        </div>
    `).join('');
}

/**
 * Clear date search and return to today
 */
function clearDateSearch() {
    const panel = document.getElementById('dateStatsPanel');
    if (panel) panel.style.display = 'none';

    const display = document.getElementById('dashDateDisplay');
    const subtitle = document.getElementById('dashDateSubtitle');
    if (display) display.textContent = "Today's Overview";
    if (subtitle) {
        const d = new Date();
        subtitle.textContent = d.toLocaleDateString('en-US', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
        });
    }

    const dateInput = document.getElementById('dateSearch');
    if (dateInput) {
        dateInput.value = new Date().toISOString().split('T')[0];
    }

    refreshDashboard();
}

/**
 * Utility: set element text content
 */
function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

/**
 * Utility: set data-count attribute
 */
function setDataCount(id, value) {
    const el = document.getElementById(id);
    if (el) el.setAttribute('data-count', value);
}

/**
 * Utility: escape HTML to prevent XSS
 */
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Auto-refresh every 60 seconds
setInterval(refreshDashboard, 60000);