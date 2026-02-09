# BD Intelligence Dashboard Improvements

## Changes Made:

### 1. IT-Only Filtering
The collection script already filters by IT NAICS codes:
- 541512: Computer Systems Design Services
- 541511: Custom Computer Programming Services  
- 541519: Other Computer Related Services

Set in `.env`:
```
NAICS_CODES=541512,541511,541519
```

To add more IT codes:
```
NAICS_CODES=541512,541511,541519,518210,541990
```

### 2. Sequential Agent Workflow
Changed from parallel buttons to numbered sequential steps:

```
Step 1: Capability Analysis (Required first)
Step 2: Generate RFI (Enabled after Step 1)
Step 3: Draft Proposal (Enabled after Step 2)  
Step 4: Generate Pricing (Enabled after Step 3)
```

Plus standalone:
- Competitive Intelligence (Can run anytime)

### 3. Modal Progress & Results
Each agent action now:
- Shows modal with progress spinner
- Displays results in the modal
- Keeps track of completion status
- Enables next step when complete

### 4. Implementation

Due to the complexity, I'll provide the key JavaScript changes needed.

Add to bd-intelligence.html before closing </script>:

```javascript
// Track agent completion status per opportunity
const agentStatus = {};

function getAgentStatus(noticeId) {
    if (!agentStatus[noticeId]) {
        agentStatus[noticeId] = {
            capabilityComplete: false,
            rfiComplete: false,
            proposalComplete: false,
            pricingComplete: false
        };
    }
    return agentStatus[noticeId];
}

// Show agent modal
function showAgentModal(title, content) {
    const modal = document.getElementById('agentModal') || createAgentModal();
    document.getElementById('agentModalTitle').textContent = title;
    document.getElementById('agentModalBody').innerHTML = content;
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
    return bsModal;
}

function createAgentModal() {
    const modalHTML = `
        <div class="modal fade" id="agentModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="agentModalTitle"></h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" id="agentModalBody"></div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    return document.getElementById('agentModal');
}

// Step 1: Capability Analysis (Required First)
async function runCapabilityAnalysisStep(noticeId) {
    const opp = await getOpportunityData(noticeId);
    if (!opp) return;
    
    const modal = showAgentModal(
        'Step 1: Capability Analysis',
        '<div class="text-center py-4"><div class="spinner-border text-primary mb-3"></div><p>Analyzing your capabilities against this opportunity...</p></div>'
    );
    
    try {
        const res = await fetch('/api/agents/capability/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({opportunity: opp})
        });
        
        const data = await res.json();
        
        if (data.capability_score) {
            // Mark as complete
            getAgentStatus(noticeId).capabilityComplete = true;
            
            // Show results
            const resultHTML = `
                <div class="alert alert-success">
                    <h5><i class="fas fa-check-circle me-2"></i>Analysis Complete!</h5>
                </div>
                
                <div class="row text-center mb-4">
                    <div class="col-md-4">
                        <h2 class="text-primary">${data.capability_score}/100</h2>
                        <p class="text-muted">Capability Score</p>
                    </div>
                    <div class="col-md-4">
                        <h4 class="text-info">${data.technical_win_probability}</h4>
                        <p class="text-muted">Win Probability</p>
                    </div>
                    <div class="col-md-4">
                        <h4>${data.requirements.matched}/${data.requirements.total}</h4>
                        <p class="text-muted">Requirements Met</p>
                    </div>
                </div>
                
                <div class="alert ${data.capability_score >= 70 ? 'alert-success' : 'alert-warning'}">
                    <strong>Recommendation:</strong> ${data.recommendation}
                </div>
                
                ${data.capability_gaps && data.capability_gaps.length > 0 ? `
                    <div class="mt-3">
                        <h6>Capability Gaps:</h6>
                        <ul>
                            ${data.capability_gaps.map(gap => 
                                `<li><span class="badge bg-${gap.severity === 'High' ? 'danger' : 'warning'}">${gap.severity}</span> ${gap.requirement}</li>`
                            ).join('')}
                        </ul>
                    </div>
                ` : ''}
                
                <div class="mt-4 text-center">
                    <button class="btn btn-primary" onclick="bootstrap.Modal.getInstance(document.getElementById('agentModal')).hide(); setTimeout(() => runRFIStep('${noticeId}'), 500)">
                        Continue to Step 2: Generate RFI →
                    </button>
                </div>
            `;
            
            document.getElementById('agentModalBody').innerHTML = resultHTML;
            
        } else {
            throw new Error(data.error || 'Analysis failed');
        }
    } catch (error) {
        document.getElementById('agentModalBody').innerHTML = `
            <div class="alert alert-danger">
                <strong>Error:</strong> ${error.message}
            </div>
        `;
    }
}

// Step 2: Generate RFI
async function runRFIStep(noticeId) {
    const status = getAgentStatus(noticeId);
    
    if (!status.capabilityComplete) {
        alert('Please complete Step 1: Capability Analysis first');
        return;
    }
    
    const opp = await getOpportunityData(noticeId);
    if (!opp) return;
    
    if (!confirm('Generate RFI response? This will take 30-60 seconds and use Claude AI.')) return;
    
    const modal = showAgentModal(
        'Step 2: Generate RFI Response',
        '<div class="text-center py-4"><div class="spinner-border text-success mb-3"></div><p>Generating professional RFI response with Claude AI...</p><p class="text-muted small">This may take 30-60 seconds</p></div>'
    );
    
    try {
        const res = await fetch('/api/agents/rfi/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({opportunity: opp})
        });
        
        const data = await res.json();
        
        if (data.status === 'success') {
            status.rfiComplete = true;
            
            document.getElementById('agentModalBody').innerHTML = `
                <div class="alert alert-success">
                    <h5><i class="fas fa-check-circle me-2"></i>RFI Response Generated!</h5>
                </div>
                
                <div class="p-3 bg-light rounded">
                    <h6>File Created:</h6>
                    <p class="font-monospace">${data.filename}</p>
                    <p class="text-muted small">Location: knowledge_graph/${data.filename}</p>
                </div>
                
                <div class="alert alert-info mt-3">
                    <strong>Next Steps:</strong>
                    <ul class="mb-0">
                        <li>Review the RFI response</li>
                        <li>Customize company-specific details</li>
                        <li>Add any additional information</li>
                        <li>Submit before deadline</li>
                    </ul>
                </div>
                
                <div class="mt-4 text-center">
                    <button class="btn btn-primary" onclick="bootstrap.Modal.getInstance(document.getElementById('agentModal')).hide(); setTimeout(() => runProposalStep('${noticeId}'), 500)">
                        Continue to Step 3: Draft Proposal →
                    </button>
                </div>
            `;
        } else {
            throw new Error(data.error || 'Generation failed');
        }
    } catch (error) {
        document.getElementById('agentModalBody').innerHTML = `
            <div class="alert alert-danger">
                <strong>Error:</strong> ${error.message}
            </div>
        `;
    }
}

// Step 3: Draft Proposal
async function runProposalStep(noticeId) {
    const status = getAgentStatus(noticeId);
    
    if (!status.rfiComplete) {
        alert('Please complete Step 2: Generate RFI first');
        return;
    }
    
    const opp = await getOpportunityData(noticeId);
    if (!opp) return;
    
    if (!confirm('Generate proposal draft? This will take 2-3 minutes and use Claude AI.')) return;
    
    const modal = showAgentModal(
        'Step 3: Draft Proposal',
        '<div class="text-center py-4"><div class="spinner-border text-info mb-3"></div><p>Drafting comprehensive proposal with Claude AI...</p><p class="text-muted small">This may take 2-3 minutes</p></div>'
    );
    
    try {
        const res = await fetch('/api/agents/proposal/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({opportunity: opp})
        });
        
        const data = await res.json();
        
        if (data.status === 'success') {
            status.proposalComplete = true;
            
            document.getElementById('agentModalBody').innerHTML = `
                <div class="alert alert-success">
                    <h5><i class="fas fa-check-circle me-2"></i>Proposal Draft Generated!</h5>
                </div>
                
                <div class="p-3 bg-light rounded">
                    <h6>File Created:</h6>
                    <p class="font-monospace">${data.filename}</p>
                    <p class="text-muted small">Location: knowledge_graph/${data.filename}</p>
                </div>
                
                <div class="alert alert-info mt-3">
                    <strong>Proposal Contains:</strong>
                    <ul class="mb-0">
                        <li>Executive Summary</li>
                        <li>Technical Approach (AI-generated)</li>
                        <li>Management Approach (AI-generated)</li>
                        <li>Past Performance</li>
                        <li>Estimated 15-20 pages</li>
                    </ul>
                </div>
                
                <div class="alert alert-warning mt-3">
                    <strong>Important:</strong> Review and customize all AI-generated content before submission. Add specific details about your team, approach, and past performance.
                </div>
                
                <div class="mt-4 text-center">
                    <button class="btn btn-primary" onclick="bootstrap.Modal.getInstance(document.getElementById('agentModal')).hide(); setTimeout(() => runPricingStep('${noticeId}'), 500)">
                        Continue to Step 4: Generate Pricing →
                    </button>
                </div>
            `;
        } else {
            throw new Error(data.error || 'Generation failed');
        }
    } catch (error) {
        document.getElementById('agentModalBody').innerHTML = `
            <div class="alert alert-danger">
                <strong>Error:</strong> ${error.message}
            </div>
        `;
    }
}

// Step 4: Generate Pricing
async function runPricingStep(noticeId) {
    const status = getAgentStatus(noticeId);
    
    if (!status.proposalComplete) {
        alert('Please complete Step 3: Draft Proposal first');
        return;
    }
    
    const opp = await getOpportunityData(noticeId);
    if (!opp) return;
    
    if (!confirm('Generate pricing with default staffing plan?\n\nPM: 1 FTE, Sr Eng: 2, Eng: 3, DevOps: 1\n12 months, $125K ODC')) return;
    
    const modal = showAgentModal(
        'Step 4: Generate Pricing',
        '<div class="text-center py-4"><div class="spinner-border text-warning mb-3"></div><p>Calculating loaded rates and generating pricing model...</p></div>'
    );
    
    try {
        const res = await fetch('/api/agents/pricing/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                opportunity: opp,
                staffing: {
                    'Program Manager': 1.0,
                    'Senior Software Engineer': 2.0,
                    'Software Engineer': 3.0,
                    'DevOps Engineer': 1.0
                },
                duration_months: 12,
                odc: {'Travel': 50000, 'Equipment': 75000}
            })
        });
        
        const data = await res.json();
        
        if (data.status === 'success' && data.igce) {
            status.pricingComplete = true;
            
            document.getElementById('agentModalBody').innerHTML = `
                <div class="alert alert-success">
                    <h5><i class="fas fa-check-circle me-2"></i>Pricing Generated!</h5>
                </div>
                
                <div class="row text-center mb-4">
                    <div class="col-md-3">
                        <h4 class="text-primary">$${(data.igce.total_value / 1000000).toFixed(2)}M</h4>
                        <p class="text-muted">Total Value</p>
                    </div>
                    <div class="col-md-3">
                        <h4 class="text-success">$${(data.igce.labor.total_cost / 1000000).toFixed(2)}M</h4>
                        <p class="text-muted">Labor</p>
                    </div>
                    <div class="col-md-3">
                        <h4 class="text-info">$${(data.igce.odc_total / 1000).toFixed(0)}K</h4>
                        <p class="text-muted">ODC</p>
                    </div>
                    <div class="col-md-3">
                        <h4 class="text-warning">$${(data.igce.monthly_burn / 1000).toFixed(0)}K</h4>
                        <p class="text-muted">Monthly</p>
                    </div>
                </div>
                
                <div class="p-3 bg-light rounded">
                    <h6>File Created:</h6>
                    <p class="font-monospace">${data.filename}</p>
                    <p class="text-muted small">Excel workbook with 3 tabs: Summary, Labor Rates, ODCs</p>
                </div>
                
                <div class="alert alert-success mt-3">
                    <h5><i class="fas fa-check-double me-2"></i>All Steps Complete!</h5>
                    <p class="mb-0">You now have everything needed for submission:</p>
                    <ul class="mb-0">
                        <li>✓ Capability Analysis</li>
                        <li>✓ RFI Response</li>
                        <li>✓ Proposal Draft</li>
                        <li>✓ Pricing Model</li>
                    </ul>
                </div>
            `;
        } else {
            throw new Error(data.error || 'Generation failed');
        }
    } catch (error) {
        document.getElementById('agentModalBody').innerHTML = `
            <div class="alert alert-danger">
                <strong>Error:</strong> ${error.message}
            </div>
        `;
    }
}
```

### 5. Update Modal HTML

Replace the agent action buttons section in the opportunity modal:

```html
<!-- Agent Actions - Sequential Workflow -->
<div class="mb-4 p-3 bg-light rounded">
    <h6 class="text-muted mb-3"><i class="fas fa-robot me-2"></i>AI Agent Workflow</h6>
    
    <div class="d-grid gap-2">
        <button class="btn btn-outline-primary" onclick="runCapabilityAnalysisStep('${opp.notice_id}')">
            <span class="badge bg-primary me-2">1</span>
            Capability Analysis
            <span class="badge bg-success ms-2" id="status-cap-${opp.notice_id}" style="display:none;">✓</span>
        </button>
        
        <button class="btn btn-outline-success" onclick="runRFIStep('${opp.notice_id}')">
            <span class="badge bg-success me-2">2</span>
            Generate RFI Response
            <span class="badge bg-success ms-2" id="status-rfi-${opp.notice_id}" style="display:none;">✓</span>
        </button>
        
        <button class="btn btn-outline-info" onclick="runProposalStep('${opp.notice_id}')">
            <span class="badge bg-info me-2">3</span>
            Draft Proposal
            <span class="badge bg-success ms-2" id="status-prop-${opp.notice_id}" style="display:none;">✓</span>
        </button>
        
        <button class="btn btn-outline-warning" onclick="runPricingStep('${opp.notice_id}')">
            <span class="badge bg-warning me-2">4</span>
            Generate Pricing
            <span class="badge bg-success ms-2" id="status-price-${opp.notice_id}" style="display:none;">✓</span>
        </button>
    </div>
    
    <hr class="my-3">
    
    <button class="btn btn-outline-secondary btn-sm w-100" onclick="runCompetitiveIntel('${opp.notice_id}')">
        <i class="fas fa-chart-line me-1"></i>Competitive Intelligence (Optional)
    </button>
</div>
```

This provides a much better user experience with:
- Clear sequential steps
- Progress modals
- Result displays
- Automatic flow to next step
- Status tracking
