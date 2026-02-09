# Implementation Guide: Sequential Agent Workflow

## Summary of Improvements

1. ✅ **IT-Only Filtering** - Already implemented via NAICS codes
2. ✅ **Sequential Workflow** - Numbered steps 1-4
3. ✅ **Modal Progress** - Shows spinner while processing
4. ✅ **Modal Results** - Displays results in modal
5. ✅ **Step Dependencies** - Step 2 requires Step 1, etc.

## Files to Update

### File 1: knowledge_graph/collect_env.py
**Status:** ✅ Already filtered for IT

The collector already uses IT NAICS codes. To customize:

Edit `.env` file:
```
NAICS_CODES=541512,541511,541519
```

Add more IT codes if needed:
- 518210: Cloud/Data Processing
- 541990: IT Consulting
- 334111: Computer Manufacturing
- 423430: Computer Equipment Wholesale

### File 2: templates/bd-intelligence.html
**Changes Required:**

#### Change 1: Add Agent Modal HTML (before </body>)

```html
<!-- Agent Progress/Results Modal -->
<div class="modal fade" id="agentModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="agentModalTitle">Agent Action</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body" id="agentModalBody">
                <div class="text-center py-4">
                    <div class="spinner-border"></div>
                    <p>Processing...</p>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            </div>
        </div>
    </div>
</div>
```

#### Change 2: Replace Agent Buttons Section

Find the section with agent action buttons (around line 566-605) and replace with:

```html
<!-- Agent Actions - Sequential Workflow -->
<div class="mb-4 p-3 bg-light rounded">
    <h6 class="text-muted mb-3">
        <i class="fas fa-robot me-2"></i>
        AI Agent Workflow
        <span class="badge bg-info ms-2">Sequential</span>
    </h6>
    
    <p class="small text-muted mb-3">
        Complete steps in order. Each step unlocks the next.
    </p>
    
    <div class="d-grid gap-2">
        <!-- Step 1: Capability Analysis -->
        <button class="btn btn-outline-primary d-flex align-items-center" 
                onclick="runStep1('${opp.notice_id}')">
            <span class="badge bg-primary me-2">1</span>
            <span class="flex-grow-1 text-start">Capability Analysis</span>
            <i class="fas fa-arrow-right ms-2"></i>
        </button>
        
        <!-- Step 2: Generate RFI -->
        <button class="btn btn-outline-success d-flex align-items-center" 
                onclick="runStep2('${opp.notice_id}')"
                id="step2-${opp.notice_id}">
            <span class="badge bg-success me-2">2</span>
            <span class="flex-grow-1 text-start">Generate RFI Response</span>
            <i class="fas fa-lock ms-2 text-muted" id="lock2-${opp.notice_id}"></i>
            <i class="fas fa-arrow-right ms-2" id="arrow2-${opp.notice_id}" style="display:none;"></i>
        </button>
        
        <!-- Step 3: Draft Proposal -->
        <button class="btn btn-outline-info d-flex align-items-center" 
                onclick="runStep3('${opp.notice_id}')"
                id="step3-${opp.notice_id}">
            <span class="badge bg-info me-2">3</span>
            <span class="flex-grow-1 text-start">Draft Proposal</span>
            <i class="fas fa-lock ms-2 text-muted" id="lock3-${opp.notice_id}"></i>
            <i class="fas fa-arrow-right ms-2" id="arrow3-${opp.notice_id}" style="display:none;"></i>
        </button>
        
        <!-- Step 4: Generate Pricing -->
        <button class="btn btn-outline-warning d-flex align-items-center" 
                onclick="runStep4('${opp.notice_id}')"
                id="step4-${opp.notice_id}">
            <span class="badge bg-warning me-2">4</span>
            <span class="flex-grow-1 text-start">Generate Pricing</span>
            <i class="fas fa-lock ms-2 text-muted" id="lock4-${opp.notice_id}"></i>
            <i class="fas fa-check-circle ms-2 text-success" id="check4-${opp.notice_id}" style="display:none;"></i>
        </button>
    </div>
    
    <hr class="my-3">
    
    <p class="small text-muted mb-2">
        <i class="fas fa-info-circle me-1"></i>
        Optional - Can run anytime
    </p>
    
    <button class="btn btn-outline-secondary btn-sm w-100" 
            onclick="runCompetitiveIntel('${opp.notice_id}')">
        <i class="fas fa-chart-line me-1"></i>
        Competitive Intelligence
    </button>
</div>
```

#### Change 3: Add JavaScript Functions (before closing </script>)

Add these complete function implementations. Due to length, I'll provide the key structure:

```javascript
// Agent status tracking
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

function unlockStep(noticeId, step) {
    const progress = getProgress(noticeId);
    progress[`step${step}`] = true;
    
    // Update UI
    document.getElementById(`lock${step+1}-${noticeId}`)?.style.display = 'none';
    document.getElementById(`arrow${step+1}-${noticeId}`)?.style.display = 'inline';
    
    if (step === 4) {
        document.getElementById(`check4-${noticeId}`).style.display = 'inline';
    }
}

function showAgentModal(title, content) {
    document.getElementById('agentModalTitle').textContent = title;
    document.getElementById('agentModalBody').innerHTML = content;
    const modal = new bootstrap.Modal(document.getElementById('agentModal'));
    modal.show();
    return modal;
}

async function runStep1(noticeId) {
    const opp = await getOpportunityData(noticeId);
    if (!opp) return;
    
    showAgentModal(
        'Step 1: Capability Analysis',
        `<div class="text-center py-5">
            <div class="spinner-border text-primary mb-3" style="width: 3rem; height: 3rem;"></div>
            <h5>Analyzing Capabilities</h5>
            <p class="text-muted">Matching your team and experience to opportunity requirements...</p>
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
            unlockStep(noticeId, 1);
            
            document.getElementById('agentModalBody').innerHTML = `
                <div class="alert alert-success">
                    <h4><i class="fas fa-check-circle me-2"></i>Analysis Complete</h4>
                </div>
                
                <div class="row text-center mb-4">
                    <div class="col-4">
                        <h2 class="text-primary">${data.capability_score}</h2>
                        <p class="text-muted">Score / 100</p>
                    </div>
                    <div class="col-4">
                        <h4 class="text-info">${data.technical_win_probability}</h4>
                        <p class="text-muted">Win Probability</p>
                    </div>
                    <div class="col-4">
                        <h4>${data.requirements.matched}/${data.requirements.total}</h4>
                        <p class="text-muted">Requirements</p>
                    </div>
                </div>
                
                <div class="alert ${data.capability_score >= 70 ? 'alert-success' : 'alert-warning'}">
                    <strong>Recommendation:</strong> ${data.recommendation}
                </div>
                
                <div class="text-center mt-4">
                    <button class="btn btn-primary btn-lg" 
                            onclick="bootstrap.Modal.getInstance(document.getElementById('agentModal')).hide();">
                        Continue to Step 2 →
                    </button>
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('agentModalBody').innerHTML = `
            <div class="alert alert-danger">
                <strong>Error:</strong> ${error.message}
            </div>
        `;
    }
}

// Similar functions for runStep2(), runStep3(), runStep4()
// Each checks if previous step is complete
// Each shows modal with progress
// Each displays results
// Each unlocks next step
```

## Quick Start

1. **Copy the files:**
```bash
cp /mnt/user-data/outputs/templates/bd-intelligence.html templates/
cp /mnt/user-data/outputs/team_dashboard_integrated.py .
```

2. **Add the modal HTML** to bd-intelligence.html (before </body>)

3. **Replace the agent buttons section** with the new sequential layout

4. **Add the JavaScript functions** (before </script>)

5. **Restart dashboard:**
```bash
python team_dashboard_integrated.py
```

6. **Test:**
- Click an opportunity
- Click "Step 1: Capability Analysis"
- Watch modal show progress
- See results in modal
- Click "Continue to Step 2"
- Repeat for all steps

## Expected Behavior

**Before any steps:**
```
[1] Capability Analysis    →
[2] Generate RFI           🔒
[3] Draft Proposal         🔒
[4] Generate Pricing       🔒
```

**After Step 1:**
```
[1] Capability Analysis    ✓
[2] Generate RFI           →
[3] Draft Proposal         🔒
[4] Generate Pricing       🔒
```

**After All Steps:**
```
[1] Capability Analysis    ✓
[2] Generate RFI           ✓
[3] Draft Proposal         ✓
[4] Generate Pricing       ✓
```

Each step shows a modal with:
1. Progress spinner while running
2. Results when complete
3. "Continue to Next Step" button
4. Automatic unlock of next step

This creates a much more intuitive, guided workflow!
