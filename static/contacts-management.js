// Contact Management System - Full Featured
// Handles CRUD, sorting, filtering, import, duplicate detection

let contacts = [];
let filteredContacts = [];
let selectedContacts = new Set();
let currentPage = 1;
let contactsPerPage = 50;
let sortColumn = 'name';
let sortDirection = 'asc';
let editingContactId = null;

// Load contacts on page load
document.addEventListener('DOMContentLoaded', () => {
    loadContacts();
    setupEventListeners();
});

function setupEventListeners() {
    // Search
    document.getElementById('searchInput').addEventListener('input', debounce(handleSearch, 300));
    
    // Upload area
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    
    uploadArea.addEventListener('click', () => fileInput.click());
    
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file) handleFileUpload(file);
    });
    
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) handleFileUpload(file);
    });
}

// Load contacts from API
async function loadContacts() {
    try {
        const response = await fetch('/api/contacts/list');
        contacts = await response.json();
        
        filteredContacts = [...contacts];
        updateStats();
        populateFilters();
        renderTable();
    } catch (error) {
        console.error('Error loading contacts:', error);
        alert('Error loading contacts');
    }
}

// Update statistics
function updateStats() {
    document.getElementById('totalContacts').textContent = contacts.length;
    
    const decisionMakers = contacts.filter(c => c.role_type === 'Decision Maker').length;
    document.getElementById('decisionMakers').textContent = decisionMakers;
    
    // Count unique agencies
    const agencies = new Set(contacts.map(c => c.agency));
    document.getElementById('agencyCount').textContent = agencies.size;
    
    // TODO: Count active contacts (need interaction data)
    document.getElementById('activeContacts').textContent = '-';
}

// Populate filter dropdowns
function populateFilters() {
    // Agencies
    const agencies = [...new Set(contacts.map(c => c.agency))].sort();
    const agencySelect = document.getElementById('filterAgency');
    agencies.forEach(agency => {
        const option = document.createElement('option');
        option.value = agency;
        option.textContent = agency;
        agencySelect.appendChild(option);
    });
    
    // Tags
    const allTags = new Set();
    contacts.forEach(c => {
        if (c.tags) {
            c.tags.forEach(tag => allTags.add(tag));
        }
    });
    const tagSelect = document.getElementById('filterTag');
    [...allTags].sort().forEach(tag => {
        const option = document.createElement('option');
        option.value = tag;
        option.textContent = tag;
        tagSelect.appendChild(option);
    });
}

// Apply filters
function applyFilters() {
    const agency = document.getElementById('filterAgency').value;
    const role = document.getElementById('filterRole').value;
    const influence = document.getElementById('filterInfluence').value;
    const tag = document.getElementById('filterTag').value;
    
    filteredContacts = contacts.filter(contact => {
        if (agency && contact.agency !== agency) return false;
        if (role && contact.role_type !== role) return false;
        if (influence && contact.influence_level !== influence) return false;
        if (tag && (!contact.tags || !contact.tags.includes(tag))) return false;
        return true;
    });
    
    currentPage = 1;
    renderTable();
}

// Search
function handleSearch() {
    const query = document.getElementById('searchInput').value.toLowerCase();
    
    if (!query) {
        filteredContacts = [...contacts];
    } else {
        filteredContacts = contacts.filter(contact => {
            const searchText = `${contact.first_name} ${contact.last_name} ${contact.title} ${contact.organization} ${contact.email}`.toLowerCase();
            return searchText.includes(query);
        });
    }
    
    currentPage = 1;
    renderTable();
}

// Sort table
function sortTable(column) {
    if (sortColumn === column) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        sortColumn = column;
        sortDirection = 'asc';
    }
    
    filteredContacts.sort((a, b) => {
        let aVal, bVal;
        
        if (column === 'name') {
            aVal = `${a.last_name} ${a.first_name}`;
            bVal = `${b.last_name} ${b.first_name}`;
        } else {
            aVal = a[column] || '';
            bVal = b[column] || '';
        }
        
        if (sortDirection === 'asc') {
            return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
        } else {
            return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
        }
    });
    
    renderTable();
}

// Render table
function renderTable() {
    const tbody = document.getElementById('contactsTable');
    tbody.innerHTML = '';
    
    const start = (currentPage - 1) * contactsPerPage;
    const end = start + contactsPerPage;
    const pageContacts = filteredContacts.slice(start, end);
    
    pageContacts.forEach(contact => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><input type="checkbox" class="contact-checkbox" data-id="${contact.id}" onchange="toggleContact(${contact.id})"></td>
            <td><span class="contact-name" onclick="viewContact(${contact.id})">${contact.first_name} ${contact.last_name}</span></td>
            <td>${contact.title || '-'}</td>
            <td>${contact.agency}</td>
            <td><span class="badge badge-${contact.role_type.toLowerCase().replace(' ', '-')}">${contact.role_type}</span></td>
            <td><span class="badge badge-${contact.influence_level.toLowerCase().replace(' ', '-')}">${contact.influence_level}</span></td>
            <td>${contact.email || contact.phone || '-'}</td>
            <td>
                <div class="action-buttons">
                    <button class="icon-btn" onclick="editContact(${contact.id})" title="Edit">✏️</button>
                    <button class="icon-btn delete" onclick="deleteContact(${contact.id})" title="Delete">🗑️</button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
    
    updatePagination();
}

// Pagination
function updatePagination() {
    const totalPages = Math.ceil(filteredContacts.length / contactsPerPage);
    document.getElementById('pageInfo').textContent = `Page ${currentPage} of ${totalPages}`;
    document.getElementById('prevBtn').disabled = currentPage === 1;
    document.getElementById('nextBtn').disabled = currentPage === totalPages;
}

function previousPage() {
    if (currentPage > 1) {
        currentPage--;
        renderTable();
    }
}

function nextPage() {
    const totalPages = Math.ceil(filteredContacts.length / contactsPerPage);
    if (currentPage < totalPages) {
        currentPage++;
        renderTable();
    }
}

// Selection
function toggleSelectAll() {
    const selectAll = document.getElementById('selectAll').checked;
    document.querySelectorAll('.contact-checkbox').forEach(cb => {
        cb.checked = selectAll;
        const id = parseInt(cb.dataset.id);
        if (selectAll) {
            selectedContacts.add(id);
        } else {
            selectedContacts.delete(id);
        }
    });
    updateBulkActionsBar();
}

function toggleContact(id) {
    if (selectedContacts.has(id)) {
        selectedContacts.delete(id);
    } else {
        selectedContacts.add(id);
    }
    updateBulkActionsBar();
}

function clearSelection() {
    selectedContacts.clear();
    document.getElementById('selectAll').checked = false;
    document.querySelectorAll('.contact-checkbox').forEach(cb => cb.checked = false);
    updateBulkActionsBar();
}

function updateBulkActionsBar() {
    const bar = document.getElementById('bulkActionsBar');
    const count = selectedContacts.size;
    
    if (count > 0) {
        bar.classList.add('active');
        document.getElementById('selectedCount').textContent = count;
    } else {
        bar.classList.remove('active');
    }
}

// Modal functions
function openAddModal() {
    editingContactId = null;
    document.getElementById('modalTitle').textContent = 'Add Contact';
    document.getElementById('contactForm').reset();
    openModal('contactModal');
}

function editContact(id) {
    const contact = contacts.find(c => c.id === id);
    if (!contact) return;
    
    editingContactId = id;
    document.getElementById('modalTitle').textContent = 'Edit Contact';
    
    // Populate form
    document.getElementById('firstName').value = contact.first_name || '';
    document.getElementById('lastName').value = contact.last_name || '';
    document.getElementById('title').value = contact.title || '';
    document.getElementById('organization').value = contact.organization || '';
    document.getElementById('department').value = contact.department || '';
    document.getElementById('agency').value = contact.agency || '';
    document.getElementById('officeSymbol').value = contact.office_symbol || '';
    document.getElementById('email').value = contact.email || '';
    document.getElementById('phone').value = contact.phone || '';
    document.getElementById('linkedinUrl').value = contact.linkedin_url || '';
    document.getElementById('location').value = contact.location || '';
    document.getElementById('clearanceLevel').value = contact.clearance_level || '';
    document.getElementById('roleType').value = contact.role_type || '';
    document.getElementById('influenceLevel').value = contact.influence_level || '';
    document.getElementById('tags').value = contact.tags ? contact.tags.join(', ') : '';
    document.getElementById('notes').value = contact.notes || '';
    
    openModal('contactModal');
}

async function saveContact(event) {
    event.preventDefault();
    
    const contactData = {
        first_name: document.getElementById('firstName').value,
        last_name: document.getElementById('lastName').value,
        title: document.getElementById('title').value,
        organization: document.getElementById('organization').value,
        department: document.getElementById('department').value,
        agency: document.getElementById('agency').value,
        office_symbol: document.getElementById('officeSymbol').value,
        email: document.getElementById('email').value,
        phone: document.getElementById('phone').value,
        linkedin_url: document.getElementById('linkedinUrl').value,
        location: document.getElementById('location').value,
        clearance_level: document.getElementById('clearanceLevel').value,
        role_type: document.getElementById('roleType').value,
        influence_level: document.getElementById('influenceLevel').value,
        notes: document.getElementById('notes').value,
        tags: document.getElementById('tags').value.split(',').map(t => t.trim()).filter(t => t)
    };
    
    try {
        const url = editingContactId 
            ? `/api/contacts/${editingContactId}`
            : '/api/contacts';
        
        const method = editingContactId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(contactData)
        });
        
        if (response.ok) {
            closeModal('contactModal');
            loadContacts();
            alert(editingContactId ? 'Contact updated!' : 'Contact added!');
        } else {
            alert('Error saving contact');
        }
    } catch (error) {
        console.error('Error saving contact:', error);
        alert('Error saving contact');
    }
}

async function deleteContact(id) {
    if (!confirm('Are you sure you want to delete this contact?')) return;
    
    try {
        const response = await fetch(`/api/contacts/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadContacts();
            alert('Contact deleted');
        } else {
            alert('Error deleting contact');
        }
    } catch (error) {
        console.error('Error deleting contact:', error);
        alert('Error deleting contact');
    }
}

function viewContact(id) {
    window.location.href = `/contacts/${id}`;
}

// Bulk operations
async function bulkDelete() {
    if (!confirm(`Delete ${selectedContacts.size} contacts?`)) return;
    
    try {
        const promises = Array.from(selectedContacts).map(id => 
            fetch(`/api/contacts/${id}`, {method: 'DELETE'})
        );
        
        await Promise.all(promises);
        clearSelection();
        loadContacts();
        alert('Contacts deleted');
    } catch (error) {
        console.error('Error deleting contacts:', error);
        alert('Error deleting contacts');
    }
}

function bulkTag() {
    const tag = prompt('Enter tag to add to selected contacts:');
    if (!tag) return;
    
    // TODO: Implement bulk tagging API
    alert('Bulk tagging feature - API endpoint needed');
}

function bulkExport() {
    const selectedContactsData = contacts.filter(c => selectedContacts.has(c.id));
    
    // Convert to CSV
    const headers = ['First Name', 'Last Name', 'Title', 'Organization', 'Agency', 'Email', 'Phone', 'Role Type', 'Influence Level'];
    const rows = selectedContactsData.map(c => [
        c.first_name, c.last_name, c.title, c.organization, c.agency,
        c.email, c.phone, c.role_type, c.influence_level
    ]);
    
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    
    // Download
    const blob = new Blob([csv], {type: 'text/csv'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `contacts_export_${Date.now()}.csv`;
    a.click();
}

// Import
function openImportModal() {
    document.getElementById('importPreview').style.display = 'none';
    document.getElementById('importBtn').style.display = 'none';
    openModal('importModal');
}

async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/contacts/import/preview', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.preview) {
            displayImportPreview(data.preview, data.total);
        } else {
            alert('Error parsing file');
        }
    } catch (error) {
        console.error('Error uploading file:', error);
        alert('Error uploading file');
    }
}

function displayImportPreview(preview, total) {
    const previewDiv = document.getElementById('importPreview');
    const previewTable = document.getElementById('previewTable');
    
    let html = '<table style="width: 100%; border-collapse: collapse;">';
    html += '<thead><tr>';
    Object.keys(preview[0]).forEach(key => {
        html += `<th style="text-align: left; padding: 0.5rem; border-bottom: 1px solid var(--border);">${key}</th>`;
    });
    html += '</tr></thead><tbody>';
    
    preview.forEach(row => {
        html += '<tr>';
        Object.values(row).forEach(val => {
            html += `<td style="padding: 0.5rem; border-bottom: 1px solid var(--border);">${val}</td>`;
        });
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    
    previewTable.innerHTML = html;
    previewDiv.style.display = 'block';
    
    document.getElementById('importCount').textContent = total;
    document.getElementById('importBtn').style.display = 'block';
}

async function confirmImport() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/contacts/import', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(`Imported ${result.imported} contacts`);
            closeModal('importModal');
            loadContacts();
        } else {
            alert('Error importing contacts');
        }
    } catch (error) {
        console.error('Error importing:', error);
        alert('Error importing contacts');
    }
}

function downloadTemplate() {
    const template = [
        ['First Name', 'Last Name', 'Title', 'Organization', 'Department', 'Agency', 'Office Symbol', 'Email', 'Phone', 'LinkedIn URL', 'Location', 'Clearance Level', 'Role Type', 'Influence Level', 'Tags', 'Notes'],
        ['John', 'Smith', 'Program Manager', 'DISA', 'IT Services', 'Department of Defense', 'DISA/GC', 'john.smith@disa.mil', '703-555-0123', 'https://linkedin.com/in/jsmith', 'Fort Meade, MD', 'Secret', 'Decision Maker', 'High', 'cloud, cybersecurity', 'Met at industry day 2024']
    ];
    
    const csv = template.map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], {type: 'text/csv'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'contact_import_template.csv';
    a.click();
}

// Find duplicates
async function findDuplicates() {
    try {
        const response = await fetch('/api/contacts/duplicates');
        const duplicates = await response.json();
        
        if (duplicates.length === 0) {
            alert('No duplicates found!');
            return;
        }
        
        displayDuplicates(duplicates);
        openModal('duplicatesModal');
    } catch (error) {
        console.error('Error finding duplicates:', error);
        alert('Error finding duplicates');
    }
}

function displayDuplicates(duplicates) {
    const list = document.getElementById('duplicatesList');
    
    let html = '';
    duplicates.forEach(group => {
        html += '<div style="background: var(--surface-light); border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin-bottom: 1rem;">';
        html += '<h4 style="color: var(--warning); margin-bottom: 1rem;">Possible Duplicates:</h4>';
        
        group.contacts.forEach(contact => {
            html += `
                <div style="padding: 0.75rem; margin-bottom: 0.5rem; background: var(--bg); border-radius: 6px;">
                    <strong>${contact.first_name} ${contact.last_name}</strong><br>
                    <span style="color: var(--text-muted); font-size: 0.9rem;">
                        ${contact.title} at ${contact.organization}<br>
                        ${contact.email || contact.phone || 'No contact info'}
                    </span>
                    <button onclick="viewContact(${contact.id})" style="margin-top: 0.5rem;" class="btn btn-secondary">View</button>
                </div>
            `;
        });
        
        html += '</div>';
    });
    
    list.innerHTML = html;
}

// Utility functions
function openModal(id) {
    document.getElementById(id).classList.add('active');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
