document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('applicationForm');
    const formStatus = document.getElementById('formStatus');
    const resultPanel = document.getElementById('resultPanel');
    const submitBtn = document.querySelector('.submit-btn');
    
    let lastResult = null;
    
    async function loadSchemes() {
        const schemeSelect = document.getElementById('schemeSelect');
        const activeCountEl = document.getElementById('activeCount');
        const inactiveCountEl = document.getElementById('inactiveCount');
        const totalCountEl = document.getElementById('totalCount');
        
        try {
            console.log('Loading schemes from API...');
            const response = await fetch('http://127.0.0.1:8000/api/schemes');
            console.log('Response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP error: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('API Result:', result);
            
            if (result.success && result.schemes && result.schemes.length > 0) {
                activeCountEl.textContent = result.active_count || 0;
                inactiveCountEl.textContent = result.inactive_count || 0;
                totalCountEl.textContent = result.total_count || 0;
                
                schemeSelect.innerHTML = '<option value="">Select a Scheme</option>';
                
                const activeSchemes = result.schemes.filter(s => s.is_active);
                const inactiveSchemes = result.schemes.filter(s => !s.is_active);
                
                if (activeSchemes.length > 0) {
                    const optgroupActive = document.createElement('optgroup');
                    optgroupActive.label = 'Active Schemes (' + activeSchemes.length + ')';
                    activeSchemes.forEach(scheme => {
                        const option = document.createElement('option');
                        option.value = scheme.scheme_id;
                        option.textContent = scheme.scheme_name + ' (' + (scheme.acronym || scheme.scheme_id) + ')';
                        option.dataset.status = 'active';
                        option.dataset.description = scheme.description;
                        optgroupActive.appendChild(option);
                    });
                    schemeSelect.appendChild(optgroupActive);
                }
                
                if (inactiveSchemes.length > 0) {
                    const optgroupInactive = document.createElement('optgroup');
                    optgroupInactive.label = 'Inactive/Closed Schemes (' + inactiveSchemes.length + ')';
                    inactiveSchemes.forEach(scheme => {
                        const option = document.createElement('option');
                        option.value = scheme.scheme_id;
                        option.textContent = scheme.scheme_name + ' (' + (scheme.acronym || scheme.scheme_id) + ')';
                        option.dataset.status = 'inactive';
                        option.dataset.description = scheme.description;
                        optgroupInactive.appendChild(option);
                    });
                    schemeSelect.appendChild(optgroupInactive);
                }
                
                // Populate active schemes list
                const activeList = document.getElementById('activeSchemesList');
                activeList.innerHTML = '';
                if (activeSchemes.length > 0) {
                    activeSchemes.slice(0, 50).forEach(scheme => {
                        const item = document.createElement('div');
                        item.className = 'scheme-item active';
                        item.innerHTML = `
                            <div class="scheme-name">${scheme.scheme_name}</div>
                            <div class="scheme-acronym">${scheme.acronym || scheme.scheme_id}</div>
                            <span class="scheme-category">${scheme.scheme_category || 'Active'}</span>
                        `;
                        item.onclick = function() {
                            document.getElementById('schemeSelect').value = scheme.scheme_id;
                            document.getElementById('schemeSelect').dispatchEvent(new Event('change'));
                        };
                        activeList.appendChild(item);
                    });
                    if (activeSchemes.length > 50) {
                        activeList.innerHTML += `<p style="color: #666; text-align: center;">...and ${activeSchemes.length - 50} more active schemes</p>`;
                    }
                } else {
                    activeList.innerHTML = '<p style="color: #666; text-align: center;">No active schemes</p>';
                }
                
                // Populate inactive schemes list
                const inactiveList = document.getElementById('inactiveSchemesList');
                inactiveList.innerHTML = '';
                if (inactiveSchemes.length > 0) {
                    inactiveSchemes.slice(0, 50).forEach(scheme => {
                        const item = document.createElement('div');
                        item.className = 'scheme-item inactive';
                        item.innerHTML = `
                            <div class="scheme-name">${scheme.scheme_name}</div>
                            <div class="scheme-acronym">${scheme.acronym || scheme.scheme_id}</div>
                            <span class="scheme-category" style="background: #999;">${scheme.status || 'Inactive'}</span>
                        `;
                        item.onclick = function() {
                            document.getElementById('schemeSelect').value = scheme.scheme_id;
                            document.getElementById('schemeSelect').dispatchEvent(new Event('change'));
                        };
                        inactiveList.appendChild(item);
                    });
                    if (inactiveSchemes.length > 50) {
                        inactiveList.innerHTML += `<p style="color: #666; text-align: center;">...and ${inactiveSchemes.length - 50} more inactive schemes</p>`;
                    }
                } else {
                    inactiveList.innerHTML = '<p style="color: #666; text-align: center;">No inactive schemes</p>';
                }
            } else {
                console.error('No schemes found or error:', result);
                schemeSelect.innerHTML = '<option value="">No schemes: ' + (result.error || 'Unknown error') + '</option>';
                activeCountEl.textContent = '0';
                inactiveCountEl.textContent = '0';
                totalCountEl.textContent = '0';
            }
        } catch (error) {
            console.error('Error loading schemes:', error);
            schemeSelect.innerHTML = '<option value="">Error: Server not running</option>';
            activeCountEl.textContent = '0';
            inactiveCountEl.textContent = '0';
            totalCountEl.textContent = '0';
        }
    }
    
    loadSchemes();
    
    window.showTab = function(tab) {
        const activeTab = document.getElementById('tabActive');
        const inactiveTab = document.getElementById('tabInactive');
        const activeList = document.getElementById('activeSchemesList');
        const inactiveList = document.getElementById('inactiveSchemesList');
        
        if (tab === 'active') {
            activeTab.classList.add('active');
            inactiveTab.classList.remove('active');
            activeList.style.display = 'block';
            inactiveList.style.display = 'none';
        } else {
            activeTab.classList.remove('active');
            inactiveTab.classList.add('active');
            activeList.style.display = 'none';
            inactiveList.style.display = 'block';
        }
    };
    
    window.updateFileName = function(input) {
        const fileNameSpan = document.getElementById(input.id + '-name');
        const uploadItem = input.closest('.upload-item');
        
        if (input.files && input.files[0]) {
            const fileName = input.files[0].name;
            fileNameSpan.textContent = fileName;
            fileNameSpan.style.color = '#4caf50';
            fileNameSpan.style.fontWeight = '600';
            uploadItem.classList.add('has-file');
        } else {
            fileNameSpan.textContent = 'Click to upload';
            fileNameSpan.style.color = '';
            fileNameSpan.style.fontWeight = '';
            uploadItem.classList.remove('has-file');
        }
    };
    
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="loading-spinner"></span> Processing...';
            formStatus.textContent = 'Submitting your application...';
            formStatus.className = 'form-status submitting';
            
            const formData = new FormData(form);
            const applicationData = {
                farmer_name: formData.get('name'),
                aadhar_number: formData.get('aadhar'),
                state: formData.get('state'),
                district: formData.get('district'),
                village: formData.get('village'),
                survey_number: formData.get('surveyNumber'),
                patta_number: formData.get('pattaNumber'),
                farmer_type: formData.get('farmerType'),
                land_area_hectares: parseFloat(formData.get('landSize')),
                crop: formData.get('cropType'),
                season: formData.get('season'),
                scheme_id: formData.get('schemeSelect'),
                loss_reason: formData.get('lossReason'),
                loss_date: formData.get('lossDate'),
                loss_percentage: parseFloat(formData.get('lossPercentage')),
                annual_income: parseFloat(formData.get('annualIncome')) || 0,
                requested_amount: parseFloat(formData.get('requestedAmount')) || 0,
                family_size: parseInt(formData.get('familySize')) || 1
            };
            
            try {
                formStatus.innerHTML = '<span class="loading-spinner"></span> Connecting to server...';
                
                const response = await fetch('http://127.0.0.1:8000/api/process-application', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(applicationData)
                });
                
                if (!response.ok) {
                    throw new Error(`Server error: ${response.status}`);
                }
                
                const result = await response.json();
                
                if (result.success) {
                    formStatus.textContent = 'Application submitted successfully!';
                    formStatus.className = 'form-status success';
                    
                    lastResult = result.data;
                    displayResults(result.data);
                    
                    formStatus.innerHTML = '<i class="fas fa-check-circle"></i> Submitted Successfully!';
                } else {
                    throw new Error(result.error || 'Unknown error');
                }
            } catch (error) {
                console.error('Error:', error);
                formStatus.textContent = 'Error: ' + error.message;
                formStatus.className = 'form-status error';
                
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Submit Application';
            } finally {
                if (formStatus.className !== 'form-status success') {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Submit Application';
                }
            }
        });
    }
    
    function displayResults(data) {
        const decision = data.final_decision;
        const confidence = (data.decision_confidence * 100).toFixed(0);
        const subsidy = data.predicted_subsidy_rs || 0;
        const scheme = data.recommended_scheme || 'N/A';
        
        const decisionCard = document.getElementById('decisionCard');
        const schemeEl = document.getElementById('schemeName');
        const subsidyEl = document.getElementById('subsidyAmount');
        const confidenceEl = document.getElementById('confidenceLevel');
        const explanationEl = document.getElementById('officerExplanation');
        
        decisionCard.className = 'result-card';
        
        if (decision === 'RECOMMEND_APPROVE') {
            decisionCard.classList.add('approve');
            document.getElementById('decisionTitle').innerHTML = '<i class="fas fa-check-circle"></i> Recommended for Approval';
        } else if (decision === 'REJECT') {
            decisionCard.classList.add('reject');
            document.getElementById('decisionTitle').innerHTML = '<i class="fas fa-times-circle"></i> Application Rejected';
        } else {
            decisionCard.classList.add('review');
            document.getElementById('decisionTitle').innerHTML = '<i class="fas fa-exclamation-triangle"></i> Review Required';
        }
        
        schemeEl.textContent = scheme;
        subsidyEl.textContent = '₹' + subsidy.toLocaleString('en-IN', {minimumFractionDigits: 2});
        confidenceEl.textContent = confidence + '%';
        explanationEl.textContent = data.officer_explanation || 'No explanation available';
        
        const agentResultsContainer = document.getElementById('agentResults');
        agentResultsContainer.innerHTML = '';
        
        if (data.agent_results && data.agent_results.length > 0) {
            data.agent_results.forEach(agent => {
                const agentItem = document.createElement('div');
                agentItem.className = 'agent-item';
                
                const statusClass = getStatusClass(agent.status);
                
                agentItem.innerHTML = `
                    <span class="agent-name">${agent.agent}</span>
                    <span class="agent-status ${statusClass}">${agent.status}</span>
                `;
                agentResultsContainer.appendChild(agentItem);
            });
        }
        
        const shapContainer = document.getElementById('shapExplanations');
        shapContainer.innerHTML = '';
        
        const shapData = data.shap_explanations || {};
        const hasShap = Object.keys(shapData).some(k => !k.endsWith('_error') && shapData[k] && Object.keys(shapData[k]).length > 0);
        
        if (hasShap) {
            Object.entries(shapData).forEach(([agent, explanation]) => {
                if (agent.endsWith('_error') || !explanation || Object.keys(explanation).length === 0) return;
                
                const shapSection = document.createElement('div');
                shapSection.className = 'shap-section';
                shapSection.innerHTML = `<h4><i class="fas fa-balance-scale"></i> SHAP: ${agent.toUpperCase()}</h4>`;
                
                const sortedFeatures = Object.entries(explanation)
                    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
                    .slice(0, 5);
                
                sortedFeatures.forEach(([feature, value]) => {
                    const maxVal = Math.max(...sortedFeatures.map(x => Math.abs(x[1])));
                    const width = maxVal > 0 ? (Math.abs(value) / maxVal * 100) : 0;
                    
                    const featureDiv = document.createElement('div');
                    featureDiv.className = 'shap-feature';
                    featureDiv.innerHTML = `
                        <span>${feature.replace(/_/g, ' ')}</span>
                        <span>${value >= 0 ? '+' : ''}${value.toFixed(3)}</span>
                    `;
                    
                    const barContainer = document.createElement('div');
                    barContainer.style.width = '100%';
                    barContainer.style.marginTop = '4px';
                    
                    const bar = document.createElement('div');
                    bar.className = 'shap-bar';
                    bar.style.width = width + '%';
                    bar.style.background = value >= 0 ? '#4caf50' : '#f44336';
                    
                    barContainer.appendChild(bar);
                    featureDiv.appendChild(barContainer);
                    shapSection.appendChild(featureDiv);
                });
                
                shapContainer.appendChild(shapSection);
            });
        } else {
            shapContainer.innerHTML = '<p style="color: #666; font-size: 0.875rem;">No SHAP explanations available</p>';
        }
        
        resultPanel.classList.remove('hidden');
        resultPanel.scrollIntoView({ behavior: 'smooth' });
        
        const officerActions = document.getElementById('officerActions');
        officerActions.style.display = 'block';
        
        document.getElementById('btnApprove').disabled = false;
        document.getElementById('btnReject').disabled = false;
        document.getElementById('btnReview').disabled = false;
        document.getElementById('decisionStatus').textContent = '';
    }
    
    function getStatusClass(status) {
        status = status.toLowerCase();
        if (status.includes('eligible') || status.includes('verify') || status.includes('confirm') || status.includes('approve') || status.includes('predicted')) {
            return 'eligible';
        } else if (status.includes('not') || status.includes('reject')) {
            return 'not-eligible';
        } else if (status.includes('pending') || status.includes('review')) {
            return 'pending';
        }
        return 'verified';
    }
    
    const districtSelect = document.getElementById('district');
    const stateSelect = document.getElementById('state');
    
    const districtMap = {
        'Maharashtra': ['Pune', 'Mumbai', 'Nagpur', 'Nashik', 'Aurangabad', 'Thane', 'Solapur', 'Kolhapur'],
        'Tamil Nadu': ['Chennai', 'Coimbatore', 'Madurai', 'Tiruchirappalli', 'Salem', 'Tiruppur', 'Vellore', 'Erode'],
        'Karnataka': ['Bangalore', 'Mysore', 'Hubli', 'Mangalore', 'Belgaum', 'Dharwad', 'Bellary', 'Tumkur'],
        'Gujarat': ['Ahmedabad', 'Surat', 'Vadodara', 'Rajkot', 'Bhavnagar', 'Jamnagar', 'Junagadh', 'Gandhinagar'],
        'Punjab': ['Ludhiana', 'Amritsar', 'Jalandhar', 'Patiala', 'Bathinda', 'Mohali', 'Hoshiarpur', 'Firozpur'],
        'Uttar Pradesh': ['Lucknow', 'Kanpur', 'Agra', 'Varanasi', 'Allahabad', 'Meerut', 'Aligarh', 'Bareilly'],
        'Rajasthan': ['Jaipur', 'Jodhpur', 'Udaipur', 'Kota', 'Bikaner', 'Ajmer', 'Pilani', 'Bhilwara'],
        'Odisha': ['Bhubaneswar', 'Cuttack', 'Rourkela', 'Berhampur', 'Sambalpur', 'Puri', 'Balasore', 'Baripada'],
        'West Bengal': ['Kolkata', 'Howrah', 'Durgapur', 'Asansol', 'Siliguri', 'Malda', 'Kharagpur', 'Bardhaman'],
        'Bihar': ['Patna', 'Gaya', 'Muzaffarpur', 'Bhagalpur', 'Darbhanga', 'Samastipur', 'Bihar Sharif', 'Arrah'],
        'Madhya Pradesh': ['Bhopal', 'Indore', 'Jabalpur', 'Gwalior', 'Ujjain', 'Sagar', 'Dewas', 'Satna'],
        'Andhra Pradesh': ['Visakhapatnam', 'Vijayawada', 'Guntur', 'Tirupati', 'Nellore', 'Kurnool', 'Rajahmundry', 'Kadapa'],
        'Telangana': ['Hyderabad', 'Warangal', 'Karimnagar', 'Khammam', 'Secunderabad', 'Nizamabad', 'Ramagundam', 'Siddipet'],
        'Kerala': ['Thiruvananthapuram', 'Kochi', 'Kozhikode', 'Thrissur', 'Kollam', 'Palakkad', 'Malappuram', 'Kannur'],
        'Assam': ['Guwahati', 'Silchar', 'Dibrugarh', 'Jorhat', 'Tezpur', 'Bongaigaon', 'Tinsukia', 'Dibrugarh']
    };
    
    if (stateSelect) {
        stateSelect.addEventListener('change', function() {
            const state = this.value;
            districtSelect.innerHTML = '<option value="">Select District</option>';
            
            if (districtMap[state]) {
                districtMap[state].forEach(district => {
                    const option = document.createElement('option');
                    option.value = district;
                    option.textContent = district;
                    districtSelect.appendChild(option);
                });
            }
        });
    }
    
    window.submitOfficerDecision = function(decision) {
        const statusEl = document.getElementById('decisionStatus');
        
        document.getElementById('btnApprove').disabled = true;
        document.getElementById('btnReject').disabled = true;
        document.getElementById('btnReview').disabled = true;
        
        let message = '';
        let color = '';
        
        if (decision === 'APPROVED') {
            message = '✓ Application APPROVED by Officer';
            color = '#4caf50';
        } else if (decision === 'REJECTED') {
            message = '✗ Application REJECTED by Officer';
            color = '#f44336';
        } else {
            message = '⚠ Application sent for REVIEW';
            color = '#ff9800';
        }
        
        statusEl.innerHTML = `<i class="fas fa-user-check"></i> ${message}`;
        statusEl.style.color = color;
        statusEl.style.fontWeight = '600';
        
        console.log('Officer Decision:', decision, 'Application ID:', lastResult?.application_id);
    };
});
