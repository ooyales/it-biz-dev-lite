// Network Visualization JavaScript
const API_BASE = '/api';

let networkData = null;
let simulation = null;
let svg = null;
let g = null;

// Color schemes
const roleColors = {
    'Decision Maker': '#FF6B6B',
    'Technical Lead': '#4ECDC4',
    'Executive': '#FFE66D',
    'Influencer': '#95E1D3',
    'default': '#00D4FF'
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadNetworkData();
    loadStats();
});

// Load network data
async function loadNetworkData() {
    try {
        const response = await fetch(`${API_BASE}/network/data`);
        networkData = await response.json();
        
        populateFilters();
        renderNetwork();
    } catch (error) {
        console.error('Error loading network data:', error);
    }
}

// Load statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/network/stats`);
        const stats = await response.json();
        
        document.getElementById('totalContacts').textContent = stats.total_contacts || 0;
        document.getElementById('totalRelationships').textContent = stats.total_relationships || 0;
        document.getElementById('totalAgencies').textContent = stats.total_agencies || 0;
        document.getElementById('decisionMakers').textContent = stats.decision_makers || 0;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Populate filter dropdowns
function populateFilters() {
    const agencies = [...new Set(networkData.nodes.map(n => n.agency))];
    const agencyFilter = document.getElementById('agencyFilter');
    
    agencies.forEach(agency => {
        const option = document.createElement('option');
        option.value = agency;
        option.textContent = agency;
        agencyFilter.appendChild(option);
    });
}

// Render network
function renderNetwork() {
    const container = document.getElementById('network');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    // Clear existing
    d3.select('#network').selectAll('*').remove();
    
    // Create SVG
    svg = d3.select('#network')
        .attr('width', width)
        .attr('height', height);
    
    // Add zoom behavior
    const zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        });
    
    svg.call(zoom);
    
    // Create container group
    g = svg.append('g');
    
    // Create force simulation
    simulation = d3.forceSimulation(networkData.nodes)
        .force('link', d3.forceLink(networkData.links)
            .id(d => d.id)
            .distance(150))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(50));
    
    // Create links
    const link = g.append('g')
        .selectAll('line')
        .data(networkData.links)
        .enter()
        .append('line')
        .attr('class', 'link')
        .attr('stroke-width', d => {
            if (d.strength === 'Strong') return 3;
            if (d.strength === 'Medium') return 2;
            return 1;
        })
        .attr('stroke-dasharray', d => d.strength === 'Weak' ? '3,3' : 'none');
    
    // Create nodes
    const node = g.append('g')
        .selectAll('g')
        .data(networkData.nodes)
        .enter()
        .append('g')
        .attr('class', 'node')
        .call(d3.drag()
            .on('start', dragStarted)
            .on('drag', dragged)
            .on('end', dragEnded));
    
    // Add circles to nodes
    node.append('circle')
        .attr('r', d => {
            if (d.influence_level === 'Very High') return 25;
            if (d.influence_level === 'High') return 20;
            if (d.influence_level === 'Medium') return 15;
            return 12;
        })
        .attr('fill', d => roleColors[d.role_type] || roleColors.default)
        .on('mouseover', showTooltip)
        .on('mouseout', hideTooltip)
        .on('click', showContactDetails);
    
    // Add labels to nodes
    node.append('text')
        .text(d => d.name)
        .attr('x', 0)
        .attr('y', 30)
        .attr('text-anchor', 'middle');
    
    // Add title (organization)
    node.append('text')
        .text(d => d.organization)
        .attr('x', 0)
        .attr('y', 42)
        .attr('text-anchor', 'middle')
        .attr('font-size', '9px')
        .attr('fill', '#8B949E');
    
    // Update positions on tick
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        
        node.attr('transform', d => `translate(${d.x},${d.y})`);
    });
}

// Drag functions
function dragStarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}

function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
}

function dragEnded(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
}

// Tooltip functions
function showTooltip(event, d) {
    const tooltip = document.getElementById('tooltip');
    const tooltipName = tooltip.querySelector('.tooltip-name');
    const tooltipInfo = tooltip.querySelector('.tooltip-info');
    
    tooltipName.textContent = d.name;
    tooltipInfo.innerHTML = `
        <strong>${d.title}</strong><br>
        ${d.organization}<br>
        ${d.agency}<br>
        Role: ${d.role_type}<br>
        Influence: ${d.influence_level}
    `;
    
    tooltip.style.left = event.pageX + 15 + 'px';
    tooltip.style.top = event.pageY + 15 + 'px';
    tooltip.classList.add('active');
}

function hideTooltip() {
    document.getElementById('tooltip').classList.remove('active');
}

// Show contact details
function showContactDetails(event, d) {
    // Shift+click = highlight immediate network without navigating
    if (event.shiftKey) {
        highlightConnectedNodes(d);
        event.stopPropagation();
        return;
    }
    
    // Regular click = navigate to detail page
    window.location.href = `/contacts/${d.id}`;
}

// Highlight a node's immediate connections
function highlightConnectedNodes(centerNode) {
    const connectedIds = new Set([centerNode.id]);
    
    // Find all links involving this node
    networkData.links.forEach(link => {
        const sourceId = link.source.id || link.source;
        const targetId = link.target.id || link.target;
        
        if (sourceId === centerNode.id) connectedIds.add(targetId);
        if (targetId === centerNode.id) connectedIds.add(sourceId);
    });
    
    // Highlight connected nodes
    d3.selectAll('.node').each(function(d) {
        const isConnected = connectedIds.has(d.id);
        const isCenter = d.id === centerNode.id;
        
        d3.select(this).select('circle')
            .attr('opacity', isConnected ? 1 : 0.15)
            .attr('stroke', isCenter ? '#FFB020' : (isConnected ? 'var(--accent)' : 'var(--border)'))
            .attr('stroke-width', isCenter ? 5 : (isConnected ? 3 : 2));
        
        d3.select(this).selectAll('text')
            .attr('opacity', isConnected ? 1 : 0.2);
    });
    
    // Highlight connected edges
    d3.selectAll('.link').each(function(link) {
        const sourceId = link.source.id || link.source;
        const targetId = link.target.id || link.target;
        const isConnected = connectedIds.has(sourceId) && connectedIds.has(targetId);
        
        d3.select(this)
            .attr('opacity', isConnected ? 1 : 0.1)
            .attr('stroke', isConnected ? 'var(--accent)' : 'var(--border)');
    });
    
    // Update search results to indicate network view
    document.getElementById('searchResults').textContent = 
        `Showing ${connectedIds.size - 1} connection${connectedIds.size - 1 !== 1 ? 's' : ''} to ${centerNode.name}`;
    document.getElementById('searchResults').style.color = 'var(--warning)';
}

// Filter network
function filterNetwork() {
    const agencyFilter = document.getElementById('agencyFilter').value;
    const roleFilter = document.getElementById('roleFilter').value;
    
    // Filter nodes
    const filteredNodes = networkData.nodes.filter(node => {
        const agencyMatch = agencyFilter === 'all' || node.agency === agencyFilter;
        const roleMatch = roleFilter === 'all' || node.role_type === roleFilter;
        return agencyMatch && roleMatch;
    });
    
    const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
    
    // Filter links
    const filteredLinks = networkData.links.filter(link => {
        return filteredNodeIds.has(link.source.id || link.source) && 
               filteredNodeIds.has(link.target.id || link.target);
    });
    
    // Update visualization
    const tempData = {
        nodes: filteredNodes,
        links: filteredLinks
    };
    
    networkData = tempData;
    renderNetwork();
}

// Highlight nodes
function highlightNodes() {
    const searchTerm = document.getElementById('searchBox').value.toLowerCase();
    
    if (!searchTerm) {
        // Reset all nodes
        d3.selectAll('.node circle')
            .attr('opacity', 1)
            .attr('stroke', 'var(--border)')
            .attr('stroke-width', 2);
        d3.selectAll('.node text')
            .attr('opacity', 1);
        document.getElementById('searchResults').textContent = '';
        return;
    }
    
    let matchCount = 0;
    const matchedNodes = [];
    
    d3.selectAll('.node').each(function(d) {
        // Search across name, organization, title, AND agency
        const match = d.name.toLowerCase().includes(searchTerm) ||
                     (d.organization || '').toLowerCase().includes(searchTerm) ||
                     (d.title || '').toLowerCase().includes(searchTerm) ||
                     (d.agency || '').toLowerCase().includes(searchTerm);
        
        if (match) {
            matchCount++;
            matchedNodes.push(d);
        }
        
        d3.select(this).select('circle')
            .attr('opacity', match ? 1 : 0.2)
            .attr('stroke', match ? 'var(--accent)' : 'var(--border)')
            .attr('stroke-width', match ? 4 : 2);
        
        // Dim text for non-matches
        d3.select(this).selectAll('text')
            .attr('opacity', match ? 1 : 0.3);
    });
    
    // Show result count
    const resultsEl = document.getElementById('searchResults');
    resultsEl.textContent = `${matchCount} contact${matchCount !== 1 ? 's' : ''} found`;
    resultsEl.style.color = matchCount > 0 ? 'var(--success)' : 'var(--warning)';
    
    // Store matched nodes for zoom feature
    window.currentMatches = matchedNodes;
}

// Zoom to highlighted matches
function zoomToMatches() {
    if (!window.currentMatches || window.currentMatches.length === 0) {
        return;
    }
    
    const matches = window.currentMatches;
    const padding = 100;
    
    // Calculate bounding box
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    
    matches.forEach(d => {
        if (d.x < minX) minX = d.x;
        if (d.x > maxX) maxX = d.x;
        if (d.y < minY) minY = d.y;
        if (d.y > maxY) maxY = d.y;
    });
    
    // Calculate transform to fit matches in view
    const width = document.getElementById('network').clientWidth;
    const height = document.getElementById('network').clientHeight;
    
    const dx = maxX - minX;
    const dy = maxY - minY;
    const x = (minX + maxX) / 2;
    const y = (minY + maxY) / 2;
    
    const scale = Math.min(
        0.9 / Math.max(dx / width, dy / height),
        4  // max zoom
    );
    
    const translate = [
        width / 2 - scale * x,
        height / 2 - scale * y
    ];
    
    // Animate zoom
    svg.transition()
        .duration(750)
        .call(
            d3.zoom().transform,
            d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
        );
}

// Reset network
function resetNetwork() {
    document.getElementById('agencyFilter').value = 'all';
    document.getElementById('roleFilter').value = 'all';
    document.getElementById('searchBox').value = '';
    
    loadNetworkData();
}
