// Data Admin Panel JavaScript
const API_BASE = '/api';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadOpportunities();
});

// Load statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/data-admin/stats`);
        const data = await response.json();
        
        document.getElementById('totalOpps').textContent = data.total || 0;
        document.getElementById('highPriority').textContent = data.high_priority || 0;
        document.getElementById('pursuing').textContent = data.pursuing || 0;
        document.getElementById('watchList').textContent = data.watch || 0;
        document.getElementById('dbSize').textContent = data.db_size || '0 KB';
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load opportunities table
async function loadOpportunities() {
    try {
        const response = await fetch(`${API_BASE}/opportunities`);
        const opportunities = await response.json();
        
        const tbody = document.getElementById('oppsTableBody');
        
        if (opportunities.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">No opportunities found</td></tr>';
            return;
        }
        
        tbody.innerHTML = opportunities.map(opp => {
            const isDemo = opp.notice_id && opp.notice_id.startsWith('DEMO');
            const statusClass = `badge-${opp.status || 'new'}`;
            
            return `
                <tr>
                    <td>
                        ${opp.notice_id || 'N/A'}
                        ${isDemo ? '<br><span style="color: var(--warning); font-size: 0.75rem;">DEMO</span>' : ''}
                    </td>
                    <td style="max-width: 300px;">${(opp.title || 'Untitled').substring(0, 50)}...</td>
                    <td><strong>${opp.fit_score ? opp.fit_score.toFixed(1) : '-'}</strong>/10</td>
                    <td>${opp.win_probability || '-'}%</td>
                    <td><span class="badge ${statusClass}">${opp.status || 'new'}</span></td>
                    <td>${opp.deadline || 'No deadline'}</td>
                    <td>${opp.type || 'N/A'}</td>
                    <td>
                        <button class="btn btn-danger" style="font-size: 0.7rem; padding: 0.3rem 0.6rem;" 
                                onclick="deleteOpportunity('${opp.notice_id}')">Delete</button>
                    </td>
                </tr>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Error loading opportunities:', error);
    }
}

// Generate demo data
async function generateDemoData() {
    const numOpps = parseInt(document.getElementById('numOpps').value) || 30;
    
    if (!confirm(`Generate ${numOpps} demo opportunities? This will create realistic dummy data.`)) {
        return;
    }
    
    try {
        showAlert('Generating demo data...', 'warning');
        
        const response = await fetch(`${API_BASE}/data-admin/generate-demo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ count: numOpps })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(`Success! Generated ${result.count} demo opportunities.`, 'success');
            loadStats();
            loadOpportunities();
        } else {
            showAlert('Error generating demo data: ' + (result.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'error');
    }
}

// Quick demo setup
async function quickDemo() {
    if (!confirm('Set up quick demo with 40 pre-configured opportunities?')) {
        return;
    }
    
    try {
        showAlert('Setting up demo...', 'warning');
        
        const response = await fetch(`${API_BASE}/data-admin/quick-demo`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(`Demo ready! Created ${result.count} opportunities.`, 'success');
            loadStats();
            loadOpportunities();
        } else {
            showAlert('Error setting up demo: ' + (result.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'error');
    }
}

// Mix demo with real data
async function mixDemoData() {
    const numOpps = parseInt(document.getElementById('mixOpps').value) || 10;
    
    if (!confirm(`Add ${numOpps} demo opportunities to existing data?`)) {
        return;
    }
    
    try {
        showAlert('Adding demo data...', 'warning');
        
        const response = await fetch(`${API_BASE}/data-admin/mix-demo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ count: numOpps })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(`Added ${result.count} demo opportunities to existing data.`, 'success');
            loadStats();
            loadOpportunities();
        } else {
            showAlert('Error: ' + (result.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'error');
    }
}

// Fetch real data
async function fetchRealData() {
    if (!confirm('Run scout to fetch real opportunities from SAM.gov? This may take a few minutes.')) {
        return;
    }
    
    try {
        showAlert('Running scout... This will take a few minutes.', 'warning');
        
        const response = await fetch(`${API_BASE}/system/run-scout`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showAlert('Scout started! Check back in a few minutes.', 'success');
            
            // Poll for completion
            setTimeout(() => {
                loadStats();
                loadOpportunities();
            }, 60000); // Check after 1 minute
        } else {
            showAlert('Error starting scout', 'error');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'error');
    }
}

// Replace with real data
async function replaceWithReal() {
    if (!confirm('WARNING: This will delete ALL demo data and fetch only real opportunities. Continue?')) {
        return;
    }
    
    try {
        // First clear demo
        await fetch(`${API_BASE}/data-admin/clear-demo`, { method: 'POST' });
        
        // Then fetch real
        showAlert('Cleared demo data. Running scout for real data...', 'warning');
        await fetchRealData();
        
    } catch (error) {
        showAlert('Error: ' + error.message, 'error');
    }
}

// Import from file
async function importFromFile() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        showAlert('Please select a file first', 'warning');
        return;
    }
    
    try {
        const text = await file.text();
        const data = JSON.parse(text);
        
        const response = await fetch(`${API_BASE}/data-admin/import`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(`Imported ${result.count} opportunities from file.`, 'success');
            loadStats();
            loadOpportunities();
        } else {
            showAlert('Error importing: ' + (result.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showAlert('Error reading file: ' + error.message, 'error');
    }
}

// Clear demo data only
async function clearDemoOnly() {
    if (!confirm('Delete all DEMO opportunities? Real data will be preserved.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/data-admin/clear-demo`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(`Deleted ${result.deleted} demo opportunities.`, 'success');
            loadStats();
            loadOpportunities();
        } else {
            showAlert('Error: ' + (result.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'error');
    }
}

// Clear all data
async function clearAllData() {
    if (!confirm('WARNING: This will delete ALL opportunities (demo AND real). This cannot be undone. Continue?')) {
        return;
    }
    
    if (!confirm('Are you ABSOLUTELY sure? All opportunity data will be permanently deleted.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/data-admin/clear-all`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(`Deleted all ${result.deleted} opportunities.`, 'success');
            loadStats();
            loadOpportunities();
        } else {
            showAlert('Error: ' + (result.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'error');
    }
}

// Clear old data
async function clearOldData() {
    if (!confirm('Delete opportunities with deadlines older than 30 days?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/data-admin/clear-old`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(`Deleted ${result.deleted} old opportunities.`, 'success');
            loadStats();
            loadOpportunities();
        } else {
            showAlert('Error: ' + (result.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'error');
    }
}

// Delete single opportunity
async function deleteOpportunity(noticeId) {
    if (!confirm(`Delete opportunity ${noticeId}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/data-admin/delete/${noticeId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showAlert('Opportunity deleted.', 'success');
            loadStats();
            loadOpportunities();
        } else {
            showAlert('Error deleting opportunity', 'error');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'error');
    }
}

// Show alert
function showAlert(message, type) {
    const alert = document.getElementById('alert');
    alert.textContent = message;
    alert.className = `alert alert-${type} show`;
    
    setTimeout(() => {
        alert.classList.remove('show');
    }, 5000);
}
