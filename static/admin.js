// Admin Panel JavaScript
const API_BASE = '/api';

let currentConfig = {};
let currentStaff = [];
let editingStaffId = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadCurrentConfig();
    loadStaffList();
    setupTagInputs();
    updateConfigPreview();
});

// Tab Switching
function switchAdminTab(tabId) {
    // Update tabs
    document.querySelectorAll('.admin-tab').forEach(tab => tab.classList.remove('active'));
    event.target.classList.add('active');
    
    // Update content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
}

// Load current configuration
async function loadCurrentConfig() {
    try {
        const response = await fetch(`${API_BASE}/config`);
        currentConfig = await response.json();
        
        populateConfigForm(currentConfig);
        updateConfigPreview();
    } catch (error) {
        console.error('Error loading config:', error);
        showAlert('Error loading configuration', 'error');
    }
}

// Populate form with current config
function populateConfigForm(config) {
    // SAM.gov settings
    document.getElementById('sam-api-key').value = config.sam_gov?.api_key || '';
    document.getElementById('lookback-days').value = config.sam_gov?.search?.lookback_days || 14;
    document.getElementById('min-value').value = config.sam_gov?.search?.value_range?.min || 50000;
    document.getElementById('max-value').value = config.sam_gov?.search?.value_range?.max || 10000000;
    
    // Opportunity types
    const oppTypes = config.sam_gov?.search?.opportunity_types || [];
    document.querySelectorAll('.opp-type').forEach(cb => {
        cb.checked = oppTypes.includes(cb.value);
    });
    
    // Keywords
    const keywords = config.sam_gov?.search?.keywords || [];
    populateTagContainer('keywords-container', 'keyword-input', keywords);
    
    // Company info
    document.getElementById('company-name').value = config.company?.name || '';
    
    // NAICS codes
    const naics = config.company?.naics_codes || [];
    populateTagContainer('naics-container', 'naics-input', naics);
    
    // Set-asides
    const setAsides = config.company?.set_asides || [];
    document.querySelectorAll('.set-aside').forEach(cb => {
        cb.checked = setAsides.includes(cb.value);
    });
    
    // Contract vehicles
    const vehicles = config.company?.contract_vehicles || [];
    populateTagContainer('vehicles-container', 'vehicle-input', vehicles);
    
    // Competitive intel
    document.getElementById('intel-enabled').checked = config.competitive_intelligence?.enabled !== false;
    document.getElementById('intel-min-value').value = config.competitive_intelligence?.triggers?.min_value || 0;
    document.getElementById('intel-lookback-years').value = config.competitive_intelligence?.lookback_years || 3;
    
    // Intel features
    const features = config.competitive_intelligence?.features || {};
    document.querySelectorAll('.intel-feature').forEach(cb => {
        cb.checked = features[cb.value] !== false;
    });
    
    // Notifications
    const email = config.notifications?.email || {};
    document.getElementById('email-enabled').checked = email.enabled === true;
    document.getElementById('smtp-server').value = email.smtp_server || 'smtp.gmail.com';
    document.getElementById('smtp-port').value = email.smtp_port || 587;
    document.getElementById('from-email').value = email.from_address || '';
    document.getElementById('email-password').value = email.password || '';
    
    const emailTo = email.to_addresses || [];
    populateTagContainer('email-to-container', 'email-to-input', emailTo);
    
    const slack = config.notifications?.slack || {};
    document.getElementById('slack-enabled').checked = slack.enabled === true;
    document.getElementById('slack-webhook').value = slack.webhook_url || '';
}

// Populate tag container
function populateTagContainer(containerId, inputId, tags) {
    const container = document.getElementById(containerId);
    const input = document.getElementById(inputId);
    
    // Clear existing tags (except input)
    Array.from(container.children).forEach(child => {
        if (child !== input) {
            child.remove();
        }
    });
    
    // Add tags
    tags.forEach(tag => {
        addTag(container, input, tag);
    });
}

// Setup tag inputs
function setupTagInputs() {
    const tagInputs = [
        { container: 'keywords-container', input: 'keyword-input' },
        { container: 'naics-container', input: 'naics-input' },
        { container: 'vehicles-container', input: 'vehicle-input' },
        { container: 'email-to-container', input: 'email-to-input' },
        { container: 'edit-skills-container', input: 'edit-skills-input' },
        { container: 'edit-certs-container', input: 'edit-certs-input' }
    ];
    
    tagInputs.forEach(({ container, input }) => {
        const containerEl = document.getElementById(container);
        const inputEl = document.getElementById(input);
        
        if (inputEl) {
            inputEl.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const value = inputEl.value.trim();
                    if (value) {
                        addTag(containerEl, inputEl, value);
                        inputEl.value = '';
                    }
                }
            });
        }
    });
}

// Add tag to container
function addTag(container, input, value) {
    const tag = document.createElement('div');
    tag.className = 'tag';
    tag.innerHTML = `
        <span>${value}</span>
        <button class="tag-remove" onclick="this.parentElement.remove()">&times;</button>
    `;
    container.insertBefore(tag, input);
}

// Get tags from container
function getTagsFromContainer(containerId) {
    const container = document.getElementById(containerId);
    const tags = [];
    
    container.querySelectorAll('.tag span').forEach(span => {
        tags.push(span.textContent);
    });
    
    return tags;
}

// Update config preview
function updateConfigPreview() {
    const config = buildConfigFromForm();
    const yaml = convertToYAML(config);
    document.getElementById('config-preview').textContent = yaml;
}

// Build config object from form
function buildConfigFromForm() {
    // Opportunity types
    const oppTypes = [];
    document.querySelectorAll('.opp-type:checked').forEach(cb => {
        oppTypes.push(cb.value);
    });
    
    // Set-asides
    const setAsides = [];
    document.querySelectorAll('.set-aside:checked').forEach(cb => {
        setAsides.push(cb.value);
    });
    
    // Intel features
    const intelFeatures = {};
    document.querySelectorAll('.intel-feature').forEach(cb => {
        intelFeatures[cb.value] = cb.checked;
    });
    
    return {
        sam_gov: {
            api_key: document.getElementById('sam-api-key').value,
            search: {
                lookback_days: parseInt(document.getElementById('lookback-days').value),
                opportunity_types: oppTypes,
                value_range: {
                    min: parseInt(document.getElementById('min-value').value),
                    max: parseInt(document.getElementById('max-value').value)
                },
                keywords: getTagsFromContainer('keywords-container')
            }
        },
        company: {
            name: document.getElementById('company-name').value || 'My Company',
            naics_codes: getTagsFromContainer('naics-container'),
            set_asides: setAsides,
            contract_vehicles: getTagsFromContainer('vehicles-container')
        },
        competitive_intelligence: {
            enabled: document.getElementById('intel-enabled').checked,
            triggers: {
                min_value: parseInt(document.getElementById('intel-min-value').value)
            },
            lookback_years: parseInt(document.getElementById('intel-lookback-years').value),
            features: intelFeatures
        },
        notifications: {
            email: {
                enabled: document.getElementById('email-enabled').checked,
                smtp_server: document.getElementById('smtp-server').value,
                smtp_port: parseInt(document.getElementById('smtp-port').value),
                from_address: document.getElementById('from-email').value,
                password: document.getElementById('email-password').value,
                to_addresses: getTagsFromContainer('email-to-container')
            },
            slack: {
                enabled: document.getElementById('slack-enabled').checked,
                webhook_url: document.getElementById('slack-webhook').value
            }
        }
    };
}

// Convert config to YAML format
function convertToYAML(obj, indent = 0) {
    let yaml = '';
    const spaces = '  '.repeat(indent);
    
    for (const [key, value] of Object.entries(obj)) {
        if (value === null || value === undefined) {
            continue;
        }
        
        if (typeof value === 'object' && !Array.isArray(value)) {
            yaml += `${spaces}${key}:\n`;
            yaml += convertToYAML(value, indent + 1);
        } else if (Array.isArray(value)) {
            yaml += `${spaces}${key}:\n`;
            value.forEach(item => {
                yaml += `${spaces}  - "${item}"\n`;
            });
        } else if (typeof value === 'boolean') {
            yaml += `${spaces}${key}: ${value}\n`;
        } else if (typeof value === 'number') {
            yaml += `${spaces}${key}: ${value}\n`;
        } else {
            yaml += `${spaces}${key}: "${value}"\n`;
        }
    }
    
    return yaml;
}

// Save all changes
async function saveAllChanges() {
    try {
        const config = buildConfigFromForm();
        
        const response = await fetch(`${API_BASE}/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        if (response.ok) {
            showAlert('Configuration saved successfully!', 'success');
            updateConfigPreview();
        } else {
            showAlert('Error saving configuration', 'error');
        }
    } catch (error) {
        console.error('Error saving config:', error);
        showAlert('Error saving configuration', 'error');
    }
}

// Load staff list
async function loadStaffList() {
    try {
        const response = await fetch(`${API_BASE}/staff`);
        currentStaff = await response.json();
        
        renderStaffList(currentStaff);
    } catch (error) {
        console.error('Error loading staff:', error);
        showAlert('Error loading staff list', 'error');
    }
}

// Render staff list
function renderStaffList(staff) {
    const container = document.getElementById('staff-list');
    
    if (!staff || staff.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: var(--text-muted);">No staff members yet. Click "Add Staff Member" to get started.</p>';
        return;
    }
    
    container.innerHTML = staff.map(member => {
        if (member.id === 'TEMPLATE') return '';
        
        const skills = member.skills?.technical?.slice(0, 3) || [];
        const clearance = member.clearance || 'None';
        
        return `
            <div class="staff-card">
                <div class="staff-info">
                    <div class="staff-name">${member.name}</div>
                    <div class="staff-title">${member.title}</div>
                    <div class="staff-meta">
                        <span>🔒 ${clearance}</span>
                        <span>💼 ${member.experience_years || 0} years</span>
                        <span>💰 $${member.hourly_rate || 0}/hr</span>
                        ${skills.length > 0 ? `<span>🛠️ ${skills.join(', ')}</span>` : ''}
                    </div>
                </div>
                <div class="staff-actions">
                    <button class="btn btn-secondary btn-sm" onclick="editStaff('${member.id}')">Edit</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteStaff('${member.id}')">Delete</button>
                </div>
            </div>
        `;
    }).join('');
}

// Add new staff
function addNewStaff() {
    editingStaffId = 'new';
    document.getElementById('staffModalTitle').textContent = 'Add New Staff Member';
    
    // Clear form
    document.getElementById('edit-staff-id').value = '';
    document.getElementById('edit-staff-name').value = '';
    document.getElementById('edit-staff-title').value = '';
    document.getElementById('edit-staff-clearance').value = '';
    document.getElementById('edit-staff-clearance-expiry').value = '';
    document.getElementById('edit-staff-labor-cat').value = '';
    document.getElementById('edit-staff-rate').value = '';
    document.getElementById('edit-staff-experience').value = '';
    document.getElementById('edit-staff-education').value = '';
    document.getElementById('edit-staff-availability').value = 'available';
    
    // Clear tags
    populateTagContainer('edit-skills-container', 'edit-skills-input', []);
    populateTagContainer('edit-certs-container', 'edit-certs-input', []);
    
    document.getElementById('staffModal').classList.add('active');
}

// Edit staff
function editStaff(staffId) {
    editingStaffId = staffId;
    const member = currentStaff.find(s => s.id === staffId);
    
    if (!member) return;
    
    document.getElementById('staffModalTitle').textContent = 'Edit Staff Member';
    document.getElementById('edit-staff-id').value = member.id;
    document.getElementById('edit-staff-name').value = member.name;
    document.getElementById('edit-staff-title').value = member.title || '';
    document.getElementById('edit-staff-clearance').value = member.clearance || '';
    document.getElementById('edit-staff-clearance-expiry').value = member.clearance_expiry || '';
    document.getElementById('edit-staff-labor-cat').value = member.labor_category || '';
    document.getElementById('edit-staff-rate').value = member.hourly_rate || '';
    document.getElementById('edit-staff-experience').value = member.experience_years || '';
    document.getElementById('edit-staff-education').value = member.education || '';
    document.getElementById('edit-staff-availability').value = member.availability || 'available';
    
    // Populate tags
    populateTagContainer('edit-skills-container', 'edit-skills-input', member.skills?.technical || []);
    populateTagContainer('edit-certs-container', 'edit-certs-input', member.skills?.certifications || []);
    
    document.getElementById('staffModal').classList.add('active');
}

// Save staff
async function saveStaff() {
    const staffData = {
        id: editingStaffId === 'new' ? generateStaffId() : document.getElementById('edit-staff-id').value,
        name: document.getElementById('edit-staff-name').value,
        title: document.getElementById('edit-staff-title').value,
        clearance: document.getElementById('edit-staff-clearance').value,
        clearance_expiry: document.getElementById('edit-staff-clearance-expiry').value,
        labor_category: document.getElementById('edit-staff-labor-cat').value,
        hourly_rate: parseFloat(document.getElementById('edit-staff-rate').value) || 0,
        experience_years: parseInt(document.getElementById('edit-staff-experience').value) || 0,
        education: document.getElementById('edit-staff-education').value,
        availability: document.getElementById('edit-staff-availability').value,
        skills: {
            technical: getTagsFromContainer('edit-skills-container'),
            certifications: getTagsFromContainer('edit-certs-container'),
            domains: []
        }
    };
    
    try {
        const response = await fetch(`${API_BASE}/staff/${staffData.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(staffData)
        });
        
        if (response.ok) {
            showAlert('Staff member saved successfully!', 'success');
            closeStaffModal();
            loadStaffList();
        } else {
            showAlert('Error saving staff member', 'error');
        }
    } catch (error) {
        console.error('Error saving staff:', error);
        showAlert('Error saving staff member', 'error');
    }
}

// Delete staff
async function deleteStaff(staffId) {
    if (!confirm('Are you sure you want to delete this staff member?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/staff/${staffId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showAlert('Staff member deleted successfully!', 'success');
            loadStaffList();
        } else {
            showAlert('Error deleting staff member', 'error');
        }
    } catch (error) {
        console.error('Error deleting staff:', error);
        showAlert('Error deleting staff member', 'error');
    }
}

// Close staff modal
function closeStaffModal() {
    document.getElementById('staffModal').classList.remove('active');
    editingStaffId = null;
}

// Generate staff ID
function generateStaffId() {
    return 'staff_' + Date.now();
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

// Listen for form changes to update preview
document.addEventListener('input', () => {
    updateConfigPreview();
});

document.addEventListener('change', () => {
    updateConfigPreview();
});
