# PATCH INSTRUCTIONS FOR BD-INTELLIGENCE.HTML

## STEP 1: Add Modal HTML before </body> tag

Find the line with `</body>` near the end of the file and add this BEFORE it:

```html
<!-- Agent Progress/Results Modal -->
<div class="modal fade" id="agentModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header bg-primary text-white">
                <h5 class="modal-title" id="agentModalTitle">
                    <i class="fas fa-robot me-2"></i>Agent Action
                </h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body" id="agentModalBody">
                <div class="text-center py-5">
                    <div class="spinner-border text-primary mb-3" style="width: 3rem; height: 3rem;"></div>
                    <p class="text-muted">Processing...</p>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            </div>
        </div>
    </div>
</div>
```

## STEP 2: Replace Agent Actions Section

Find this section (around line 566-605):
```html
<!-- Agent Actions -->
<div class="mb-4 p-3 bg-light rounded">
```

Replace the ENTIRE section (from the opening div through the closing div) with:

```html
<!-- Agent Actions - Sequential Workflow -->
<div class="mb-4 p-3 border rounded" style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);">
    <div class="d-flex align-items-center mb-3">
        <i class="fas fa-robot text-primary me-2" style="font-size: 1.5rem;"></i>
        <h6 class="mb-0">AI Agent Workflow</h6>
        <span class="badge bg-primary ms-auto">Sequential</span>
    </div>
    
    <p class="small text-muted mb-3">
        <i class="fas fa-info-circle me-1"></i>
        Complete each step in order to prepare your response.
    </p>
    
    <div class="d-grid gap-2">
        <button class="btn btn-outline-primary btn-lg d-flex align-items-center justify-content-between" 
                onclick="runStep1('${opp.notice_id}')"
                id="step1-btn-${opp.notice_id}">
            <div class="d-flex align-items-center">
                <span class="badge bg-primary me-2" style="font-size: 1rem;">1</span>
                <span>Capability Analysis</span>
            </div>
            <i class="fas fa-arrow-right"></i>
        </button>
        
        <button class="btn btn-outline-success btn-lg d-flex align-items-center justify-content-between" 
                onclick="runStep2('${opp.notice_id}')"
                id="step2-btn-${opp.notice_id}"
                disabled>
            <div class="d-flex align-items-center">
                <span class="badge bg-success me-2" style="font-size: 1rem;">2</span>
                <span>Generate RFI Response</span>
            </div>
            <i class="fas fa-lock" id="lock2-${opp.notice_id}"></i>
            <i class="fas fa-arrow-right" id="arrow2-${opp.notice_id}" style="display:none;"></i>
        </button>
        
        <button class="btn btn-outline-info btn-lg d-flex align-items-center justify-content-between" 
                onclick="runStep3('${opp.notice_id}')"
                id="step3-btn-${opp.notice_id}"
                disabled>
            <div class="d-flex align-items-center">
                <span class="badge bg-info me-2" style="font-size: 1rem;">3</span>
                <span>Draft Proposal</span>
            </div>
            <i class="fas fa-lock" id="lock3-${opp.notice_id}"></i>
            <i class="fas fa-arrow-right" id="arrow3-${opp.notice_id}" style="display:none;"></i>
        </button>
        
        <button class="btn btn-outline-warning btn-lg d-flex align-items-center justify-content-between" 
                onclick="runStep4('${opp.notice_id}')"
                id="step4-btn-${opp.notice_id}"
                disabled>
            <div class="d-flex align-items-center">
                <span class="badge bg-warning me-2" style="font-size: 1rem;">4</span>
                <span>Generate Pricing</span>
            </div>
            <i class="fas fa-lock" id="lock4-${opp.notice_id}"></i>
            <i class="fas fa-check-circle text-success" id="check4-${opp.notice_id}" style="display:none;"></i>
        </button>
    </div>
    
    <hr class="my-3">
    
    <p class="small text-muted mb-2">
        <i class="fas fa-lightbulb me-1"></i>
        Optional - Can run independently
    </p>
    
    <button class="btn btn-outline-secondary btn-sm w-100" 
            onclick="runCompetitiveIntelModal('${opp.notice_id}')">
        <i class="fas fa-chart-line me-2"></i>
        Competitive Intelligence Analysis
    </button>
</div>
```

## STEP 3: Replace JavaScript Functions

Find the existing agent functions (runCapabilityAnalysis, generateRFI, etc.) and REPLACE them ALL with these new versions.

Find this section (around line 700+):
```javascript
async function runCapabilityAnalysis(noticeId) {
```

Replace ALL the old agent functions through the end with:

```javascript
// ==================================================================
// SEQUENTIAL AGENT WORKFLOW WITH MODALS
// ==================================================================

// Track completion status
const agentProgress = {};

function getProgress(noticeId) {
    if (!agentProgress[noticeId]) {
        agentProgress[noticeId] = {
            step1: false,
            step2: false,
            step3: false,
            step4: false
        };
    }
    return agentProgress[noticeId];
}

function unlockNextStep(noticeId, currentStep) {
    const progress = getProgress(noticeId);
    progress[`step${currentStep}`] = true;
    
    const nextStep = currentStep + 1;
    if (nextStep <= 4) {
        // Enable next button
        const nextBtn = document.getElementById(`step${nextStep}-btn-${noticeId}`);
        if (nextBtn) {
            nextBtn.disabled = false;
            nextBtn.classList.remove('opacity-50');
        }
        
        // Update icons
        document.getElementById(`lock${nextStep}-${noticeId}`)?.setAttribute('style', 'display:none;');
        document.getElementById(`arrow${nextStep}-${noticeId}`)?.setAttribute('style', 'display:inline;');
    }
    
    // Mark current step complete
    if (currentStep === 4) {
        document.getElementById(`check4-${noticeId}`)?.setAttribute('style', 'display:inline;');
    }
}

function showAgentModal(title, content) {
    document.getElementById('agentModalTitle').innerHTML = `<i class="fas fa-robot me-2"></i>${title}`;
    document.getElementById('agentModalBody').innerHTML = content;
    const modal = new bootstrap.Modal(document.getElementById('agentModal'));
    modal.show();
    return modal;
}

// STEP 1: Capability Analysis
async function runStep1(noticeId) {
    const opp = await getOpportunityData(noticeId);
    if (!opp) return;
    
    showAgentModal(
        'Step 1: Capability Analysis',
        `<div class="text-center py-5">
            <div class="spinner-border text-primary mb-4" style="width: 4rem; height: 4rem;"></div>
            <h4>Analyzing Capabilities</h4>
            <p class="text-muted">Matching your team and experience against opportunity requirements...</p>
            <div class="progress mt-4" style="height: 4px;">
                <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 100%"></div>
            </div>
        </div>`
    );
    
    try {
        const res = await fetch('/api/agents/capability/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({opportunity: opp})
        });
        
        const data = await res.json();
        
        if (data.capability_score) {
            unlockNextStep(noticeId, 1);
            
            const scoreColor = data.capability_score >= 80 ? 'success' : 
                             data.capability_score >= 60 ? 'warning' : 'danger';
            
            document.getElementById('agentModalBody').innerHTML = `
                <div class="alert alert-success mb-4">
                    <h4 class="alert-heading">
                        <i class="fas fa-check-circle me-2"></i>Analysis Complete!
                    </h4>
                    <p class="mb-0">Your capabilities have been evaluated against this opportunity.</p>
                </div>
                
                <div class="row text-center mb-4">
                    <div class="col-md-4">
                        <div class="p-3 border rounded">
                            <h1 class="text-${scoreColor} mb-0">${data.capability_score}</h1>
                            <p class="text-muted mb-0">Capability Score</p>
                            <small class="text-muted">out of 100</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="p-3 border rounded">
                            <h4 class="text-info mb-0">${data.technical_win_probability}</h4>
                            <p class="text-muted mb-0">Win Probability</p>
                            <small class="text-muted">technical fit</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="p-3 border rounded">
                            <h2 class="mb-0">${data.requirements.matched}<small class="text-muted">/${data.requirements.total}</small></h2>
                            <p class="text-muted mb-0">Requirements Met</p>
                            <small class="text-muted">${Math.round(data.requirements.matched/data.requirements.total*100)}% match</small>
                        </div>
                    </div>
                </div>
                
                <div class="alert alert-${scoreColor}">
                    <strong><i class="fas fa-lightbulb me-2"></i>Recommendation:</strong><br>
                    ${data.recommendation}
                </div>
                
                ${data.capability_gaps && data.capability_gaps.length > 0 ? `
                    <div class="mt-3">
                        <h6><i class="fas fa-exclamation-triangle me-2 text-warning"></i>Capability Gaps:</h6>
                        <ul class="list-group">
                            ${data.capability_gaps.slice(0, 3).map(gap => 
                                `<li class="list-group-item d-flex justify-content-between align-items-center">
                                    ${gap.requirement}
                                    <span class="badge bg-${gap.severity === 'High' ? 'danger' : 'warning'}">${gap.severity}</span>
                                </li>`
                            ).join('')}
                        </ul>
                    </div>
                ` : '<div class="alert alert-success"><i class="fas fa-check me-2"></i>No critical capability gaps identified!</div>'}
                
                <div class="text-center mt-4">
                    <p class="text-muted mb-3">
                        <i class="fas fa-unlock me-2"></i>Step 2 is now unlocked
                    </p>
                    <button class="btn btn-success btn-lg px-5" 
                            onclick="bootstrap.Modal.getInstance(document.getElementById('agentModal')).hide();">
                        <i class="fas fa-arrow-right me-2"></i>Continue to Step 2
                    </button>
                </div>
            `;
        } else {
            throw new Error(data.error || 'Analysis failed');
        }
    } catch (error) {
        document.getElementById('agentModalBody').innerHTML = `
            <div class="alert alert-danger">
                <h5><i class="fas fa-exclamation-triangle me-2"></i>Error</h5>
                <p class="mb-0">${error.message}</p>
            </div>
        `;
    }
}

// STEP 2: Generate RFI
async function runStep2(noticeId) {
    const progress = getProgress(noticeId);
    if (!progress.step1) {
        alert('⚠️ Please complete Step 1: Capability Analysis first');
        return;
    }
    
    const opp = await getOpportunityData(noticeId);
    if (!opp) return;
    
    if (!confirm('Generate RFI response?\n\nThis will use Claude AI and take 30-60 seconds.')) return;
    
    showAgentModal(
        'Step 2: Generate RFI Response',
        `<div class="text-center py-5">
            <div class="spinner-border text-success mb-4" style="width: 4rem; height: 4rem;"></div>
            <h4>Generating RFI Response</h4>
            <p class="text-muted">Claude AI is writing a professional RFI response...</p>
            <p class="small text-muted"><i class="fas fa-clock me-1"></i>This typically takes 30-60 seconds</p>
            <div class="progress mt-4" style="height: 4px;">
                <div class="progress-bar bg-success progress-bar-striped progress-bar-animated" style="width: 100%"></div>
            </div>
        </div>`
    );
    
    try {
        const res = await fetch('/api/agents/rfi/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({opportunity: opp})
        });
        
        const data = await res.json();
        
        if (data.status === 'success') {
            unlockNextStep(noticeId, 2);
            
            document.getElementById('agentModalBody').innerHTML = `
                <div class="alert alert-success">
                    <h4><i class="fas fa-check-circle me-2"></i>RFI Response Generated!</h4>
                </div>
                
                <div class="card mb-3">
                    <div class="card-body">
                        <h6><i class="fas fa-file-word me-2"></i>Document Created:</h6>
                        <p class="font-monospace text-primary">${data.filename}</p>
                        <p class="text-muted small mb-0">
                            <i class="fas fa-folder me-1"></i>
                            Location: knowledge_graph/${data.filename}
                        </p>
                    </div>
                </div>
                
                <div class="alert alert-info">
                    <h6><i class="fas fa-tasks me-2"></i>Next Steps:</h6>
                    <ul class="mb-0">
                        <li>Open and review the RFI response</li>
                        <li>Customize company-specific details</li>
                        <li>Add any additional required information</li>
                        <li>Submit before the deadline</li>
                    </ul>
                </div>
                
                <div class="text-center mt-4">
                    <p class="text-muted mb-3">
                        <i class="fas fa-unlock me-2"></i>Step 3 is now unlocked
                    </p>
                    <button class="btn btn-info btn-lg px-5" 
                            onclick="bootstrap.Modal.getInstance(document.getElementById('agentModal')).hide();">
                        <i class="fas fa-arrow-right me-2"></i>Continue to Step 3
                    </button>
                </div>
            `;
        } else {
            throw new Error(data.error || 'Generation failed');
        }
    } catch (error) {
        document.getElementById('agentModalBody').innerHTML = `
            <div class="alert alert-danger">
                <h5><i class="fas fa-exclamation-triangle me-2"></i>Error</h5>
                <p class="mb-0">${error.message}</p>
            </div>
        `;
    }
}

// STEP 3: Draft Proposal  
async function runStep3(noticeId) {
    const progress = getProgress(noticeId);
    if (!progress.step2) {
        alert('⚠️ Please complete Step 2: Generate RFI first');
        return;
    }
    
    const opp = await getOpportunityData(noticeId);
    if (!opp) return;
    
    if (!confirm('Generate proposal draft?\n\nThis will use Claude AI and take 2-3 minutes.')) return;
    
    showAgentModal(
        'Step 3: Draft Proposal',
        `<div class="text-center py-5">
            <div class="spinner-border text-info mb-4" style="width: 4rem; height: 4rem;"></div>
            <h4>Drafting Proposal</h4>
            <p class="text-muted">Claude AI is writing a comprehensive proposal draft...</p>
            <p class="small text-muted"><i class="fas fa-clock me-1"></i>This typically takes 2-3 minutes</p>
            <div class="progress mt-4" style="height: 4px;">
                <div class="progress-bar bg-info progress-bar-striped progress-bar-animated" style="width: 100%"></div>
            </div>
        </div>`
    );
    
    try {
        const res = await fetch('/api/agents/proposal/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({opportunity: opp})
        });
        
        const data = await res.json();
        
        if (data.status === 'success') {
            unlockNextStep(noticeId, 3);
            
            document.getElementById('agentModalBody').innerHTML = `
                <div class="alert alert-success">
                    <h4><i class="fas fa-check-circle me-2"></i>Proposal Draft Complete!</h4>
                </div>
                
                <div class="card mb-3">
                    <div class="card-body">
                        <h6><i class="fas fa-file-alt me-2"></i>Document Created:</h6>
                        <p class="font-monospace text-primary">${data.filename}</p>
                        <p class="text-muted small mb-0">
                            <i class="fas fa-folder me-1"></i>
                            Location: knowledge_graph/${data.filename}
                        </p>
                    </div>
                </div>
                
                <div class="alert alert-info">
                    <h6><i class="fas fa-file-word me-2"></i>Proposal Contains:</h6>
                    <ul class="mb-0">
                        <li>Executive Summary</li>
                        <li>Technical Approach (AI-generated)</li>
                        <li>Management Approach (AI-generated)</li>
                        <li>Past Performance Section</li>
                        <li>Estimated 15-20 pages</li>
                    </ul>
                </div>
                
                <div class="alert alert-warning">
                    <strong><i class="fas fa-exclamation-triangle me-2"></i>Important:</strong>
                    Review and customize all AI-generated content. Add specific details about your team, methodologies, and past performance.
                </div>
                
                <div class="text-center mt-4">
                    <p class="text-muted mb-3">
                        <i class="fas fa-unlock me-2"></i>Step 4 is now unlocked
                    </p>
                    <button class="btn btn-warning btn-lg px-5" 
                            onclick="bootstrap.Modal.getInstance(document.getElementById('agentModal')).hide();">
                        <i class="fas fa-arrow-right me-2"></i>Continue to Step 4
                    </button>
                </div>
            `;
        } else {
            throw new Error(data.error || 'Generation failed');
        }
    } catch (error) {
        document.getElementById('agentModalBody').innerHTML = `
            <div class="alert alert-danger">
                <h5><i class="fas fa-exclamation-triangle me-2"></i>Error</h5>
                <p class="mb-0">${error.message}</p>
            </div>
        `;
    }
}

// STEP 4: Generate Pricing
async function runStep4(noticeId) {
    const progress = getProgress(noticeId);
    if (!progress.step3) {
        alert('⚠️ Please complete Step 3: Draft Proposal first');
        return;
    }
    
    const opp = await getOpportunityData(noticeId);
    if (!opp) return;
    
    if (!confirm('Generate pricing?\n\nDefault: PM (1), Sr Eng (2), Eng (3), DevOps (1)\n12 months, $125K ODC')) return;
    
    showAgentModal(
        'Step 4: Generate Pricing',
        `<div class="text-center py-5">
            <div class="spinner-border text-warning mb-4" style="width: 4rem; height: 4rem;"></div>
            <h4>Generating Pricing Model</h4>
            <p class="text-muted">Calculating loaded labor rates and total contract value...</p>
            <div class="progress mt-4" style="height: 4px;">
                <div class="progress-bar bg-warning progress-bar-striped progress-bar-animated" style="width: 100%"></div>
            </div>
        </div>`
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
            unlockNextStep(noticeId, 4);
            
            document.getElementById('agentModalBody').innerHTML = `
                <div class="alert alert-success">
                    <h4><i class="fas fa-check-circle me-2"></i>Pricing Model Complete!</h4>
                </div>
                
                <div class="row text-center mb-4">
                    <div class="col-md-3">
                        <div class="p-3 border rounded bg-light">
                            <h3 class="text-primary mb-0">$${(data.igce.total_value / 1000000).toFixed(2)}M</h3>
                            <p class="text-muted mb-0 small">Total Value</p>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="p-3 border rounded bg-light">
                            <h4 class="text-success mb-0">$${(data.igce.labor.total_cost / 1000000).toFixed(2)}M</h4>
                            <p class="text-muted mb-0 small">Labor Cost</p>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="p-3 border rounded bg-light">
                            <h4 class="text-info mb-0">$${(data.igce.odc_total / 1000).toFixed(0)}K</h4>
                            <p class="text-muted mb-0 small">ODC Cost</p>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="p-3 border rounded bg-light">
                            <h4 class="text-warning mb-0">$${(data.igce.monthly_burn / 1000).toFixed(0)}K</h4>
                            <p class="text-muted mb-0 small">Monthly Burn</p>
                        </div>
                    </div>
                </div>
                
                <div class="card mb-3">
                    <div class="card-body">
                        <h6><i class="fas fa-file-excel me-2 text-success"></i>Excel Workbook Created:</h6>
                        <p class="font-monospace text-primary">${data.filename}</p>
                        <p class="text-muted small mb-0">
                            Contains: Summary, Labor Rates, ODC Breakdown
                        </p>
                    </div>
                </div>
                
                <div class="alert alert-success">
                    <h5><i class="fas fa-check-double me-2"></i>Workflow Complete!</h5>
                    <p class="mb-2">You now have everything needed for submission:</p>
                    <ul class="mb-0">
                        <li><i class="fas fa-check text-success me-2"></i>Capability Analysis Complete</li>
                        <li><i class="fas fa-check text-success me-2"></i>RFI Response Generated</li>
                        <li><i class="fas fa-check text-success me-2"></i>Proposal Draft Created</li>
                        <li><i class="fas fa-check text-success me-2"></i>Pricing Model Ready</li>
                    </ul>
                </div>
                
                <div class="text-center mt-4">
                    <button class="btn btn-success btn-lg px-5" 
                            onclick="bootstrap.Modal.getInstance(document.getElementById('agentModal')).hide();">
                        <i class="fas fa-check me-2"></i>All Done!
                    </button>
                </div>
            `;
        } else {
            throw new Error(data.error || 'Generation failed');
        }
    } catch (error) {
        document.getElementById('agentModalBody').innerHTML = `
            <div class="alert alert-danger">
                <h5><i class="fas fa-exclamation-triangle me-2"></i>Error</h5>
                <p class="mb-0">${error.message}</p>
            </div>
        `;
    }
}

// Competitive Intelligence (can run anytime)
async function runCompetitiveIntelModal(noticeId) {
    const opp = await getOpportunityData(noticeId);
    if (!opp) return;
    
    showAgentModal(
        'Competitive Intelligence',
        `<div class="text-center py-5">
            <div class="spinner-border text-secondary mb-4" style="width: 4rem; height: 4rem;"></div>
            <h4>Analyzing Competition</h4>
            <p class="text-muted">Identifying incumbents and teaming partners...</p>
        </div>`
    );
    
    try {
        const res = await fetch('/api/agents/competitive/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                agency: opp.agency,
                naics: opp.naics
            })
        });
        
        const data = await res.json();
        
        const incumbents = data.incumbents || [];
        const partners = data.teaming_partners || [];
        
        document.getElementById('agentModalBody').innerHTML = `
            <div class="alert alert-info">
                <h5><i class="fas fa-chart-line me-2"></i>Intelligence Gathered</h5>
            </div>
            
            <div class="row mb-3">
                <div class="col-6">
                    <div class="p-3 border rounded text-center">
                        <h2 class="mb-0">${incumbents.length}</h2>
                        <p class="text-muted mb-0">Incumbents Found</p>
                    </div>
                </div>
                <div class="col-6">
                    <div class="p-3 border rounded text-center">
                        <h2 class="mb-0">${partners.length}</h2>
                        <p class="text-muted mb-0">Potential Partners</p>
                    </div>
                </div>
            </div>
            
            ${incumbents.length > 0 ? `
                <h6>Top Incumbents:</h6>
                <ul class="list-group mb-3">
                    ${incumbents.slice(0, 5).map(inc => 
                        `<li class="list-group-item d-flex justify-content-between">
                            <span>${inc.name || inc.company}</span>
                            <span class="badge bg-primary">${inc.contract_count || inc.contracts || 0} contracts</span>
                        </li>`
                    ).join('')}
                </ul>
            ` : '<p class="text-muted">No incumbent data available</p>'}
            
            <p class="text-muted small">
                <i class="fas fa-info-circle me-1"></i>
                Full details logged to browser console (F12)
            </p>
        `;
        
        console.log('Competitive Intelligence Results:', data);
        
    } catch (error) {
        document.getElementById('agentModalBody').innerHTML = `
            <div class="alert alert-danger">
                <h5><i class="fas fa-exclamation-triangle me-2"></i>Error</h5>
                <p class="mb-0">${error.message}</p>
            </div>
        `;
    }
}

// Keep the rest of your existing functions below...
```

Save this file as `/mnt/user-data/outputs/BD_INTELLIGENCE_PATCHES.md` and follow the instructions to update your bd-intelligence.html file.

The patches are organized as:
1. Add modal HTML (1 block)
2. Replace agent buttons section (1 block)  
3. Replace JavaScript functions (1 large block)

This gives you the complete, production-ready sequential workflow!
