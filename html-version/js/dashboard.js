// API Configuration
const API_BASE_URL = '/api';

// Selected lot, duration, and spot for booking
let selectedLot = null;
let userVehicles = [];
let selectedSpotId = null;
let bookingDuration = 1;

// Get auth token from localStorage
function getAuthToken() {
    return localStorage.getItem('authToken');
}

// Check if user is logged in
function checkAuth() {
    const token = getAuthToken();
    if (!token) {
        window.location.href = 'login.html';
        return false;
    }

    // Display user name
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const userName = document.getElementById('userName');
    if (userName && user.name) {
        userName.textContent = user.name;
    }
    return true;
}

// API call helper
async function apiCall(endpoint, options = {}) {
    const token = getAuthToken();
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Request failed');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Fetch user's vehicles
async function loadUserVehicles() {
    try {
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        if (user.id) {
            const profile = await apiCall(`/users/me`);
            userVehicles = profile.vehicles || [];
            if (profile.vehicle_number) {
                userVehicles.push(profile.vehicle_number);
            }
            console.log('User vehicles loaded:', userVehicles);
        }
    } catch (error) {
        console.error('Error loading user vehicles:', error);
        userVehicles = [];
    }
}

// Populate vehicle dropdown
function populateVehicleDropdown() {
    const selectEl = document.getElementById('modalVehicleNumber');
    const hintEl = document.getElementById('vehicleHint');
    
    // Clear existing options except first one
    selectEl.innerHTML = '<option value="">-- Select vehicle from account --</option>';
    
    if (userVehicles && userVehicles.length > 0) {
        userVehicles.forEach(vehicle => {
            const vehicleNum = typeof vehicle === 'string' ? vehicle : vehicle.vehicle_number;
            const option = document.createElement('option');
            option.value = vehicleNum;
            option.textContent = vehicleNum;
            selectEl.appendChild(option);
        });
        if (hintEl) hintEl.style.display = 'none';
    } else {
        if (hintEl) hintEl.style.display = 'block';
    }
}

// Update pricing based on duration
function updatePricingDisplay() {
    const durationEl = document.getElementById('bookingDuration');
    bookingDuration = parseInt(durationEl.value) || 1;

    if (!selectedLot) return;

    const hourlyRate = selectedLot.dynamic_rate || selectedLot.hourly_rate || 0;
    const totalCost = bookingDuration * hourlyRate;
    const isSurge = selectedLot.price_multiplier > 1;

    document.getElementById('modalEstimatedCost').textContent = `₹${totalCost.toFixed(2)} for ${bookingDuration}h`;
    
    const pricingInfo = document.getElementById('pricingInfo');
    if (pricingInfo) {
        if (isSurge) {
            pricingInfo.textContent = `⚠️ Surge pricing active (${selectedLot.price_multiplier}x multiplier)`;
        } else {
            pricingInfo.textContent = 'Pricing calculated automatically';
        }
    }
}

// Load parking lots
async function loadParkingLots(query = '', pinCode = '') {
    try {
        const params = new URLSearchParams();
        if (query) params.append('q', query);
        if (pinCode) params.append('pin_code', pinCode);

        const lots = await apiCall(`/parking/search?${params}`);
        renderParkingLots(lots);
    } catch (error) {
        console.error('Error loading parking lots:', error);
        showAlert('Failed to load parking lots', 'error');
    }
}

// Render parking lots
function renderParkingLots(lots) {
    const container = document.getElementById('parkingLotsContainer');

    if (lots.length === 0) {
        container.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 3rem;">
                <p style="color: hsl(var(--muted-foreground)); font-size: 1.125rem;">No parking lots found</p>
                <p style="color: hsl(var(--muted-foreground)); font-size: 0.875rem; margin-top: 0.5rem;">Try adjusting your search criteria</p>
            </div>
        `;
        return;
    }

    container.innerHTML = lots.map(lot => {
        const isSurge = lot.price_multiplier > 1;
        const surgeLabel = lot.price_multiplier >= 2 ? '🔥 High Demand' :
            lot.price_multiplier >= 1.5 ? '📈 Surge Pricing' :
                lot.price_multiplier > 1 ? '💹 Busy' : '';
        
        const timeLabel = lot.is_peak_hour ? '⏰ Peak Hours' : '🌙 Off-Peak';
        const timeColor = lot.is_peak_hour ? 'hsl(var(--warning))' : 'hsl(142 76% 36%)';

        return `
        <div class="parking-card">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                <div>
                    <h3 class="parking-name">${lot.name}</h3>
                    <p class="parking-location">📍 ${lot.address}, ${lot.city}</p>
                    <p style="color: hsl(var(--muted-foreground)); font-size: 0.875rem;">PIN: ${lot.pin_code}</p>
                    <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem; flex-wrap: wrap;">
                        <span style="font-size: 0.75rem; padding: 0.25rem 0.75rem; background: hsl(var(--accent) / 0.1); color: ${timeColor}; border-radius: 4px; font-weight: 600;">
                            ${timeLabel}
                        </span>
                        ${isSurge ? `<span style="font-size: 0.75rem; padding: 0.25rem 0.75rem; background: hsl(var(--destructive) / 0.1); color: hsl(var(--destructive)); border-radius: 4px; font-weight: 600;">
                            ${surgeLabel}
                        </span>` : ''}
                    </div>
                </div>
                <div style="text-align: right;">
                    ${isSurge ? `
                        <div style="font-size: 0.75rem; color: hsl(var(--muted-foreground)); text-decoration: line-through;">₹${lot.base_rate}/hr</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: hsl(var(--destructive));">₹${lot.dynamic_rate}/hr</div>
                        <div style="font-size: 0.75rem; color: hsl(var(--muted-foreground));">(${lot.price_multiplier}x surge)</div>
                    ` : `
                        <div style="font-size: 1.5rem; font-weight: 700; color: hsl(var(--primary));">₹${lot.dynamic_rate || lot.hourly_rate}/hr</div>
                        ${lot.price_multiplier < 1 ? `<div style="font-size: 0.75rem; color: hsl(142 76% 36%); font-weight: 600;">(${(lot.price_multiplier * 100).toFixed(0)}% off-peak)</div>` : ''}
                    `}
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-sm); margin-bottom: var(--space-md);">
                <div style="text-align: center; padding: var(--space-sm); background: hsl(142 76% 36% / 0.1); border-radius: var(--radius);">
                    <div style="font-size: 0.75rem; color: hsl(var(--muted-foreground));">REAL-TIME</div>
                    <div style="font-size: 1.25rem; font-weight: 700; color: hsl(142 76% 36%);">${lot.available_spots} Available</div>
                </div>
                <div style="text-align: center; padding: var(--space-sm); background: hsl(var(--secondary)); border-radius: var(--radius);">
                    <div style="font-size: 0.75rem; color: hsl(var(--muted-foreground));">OCCUPANCY</div>
                    <div style="font-size: 1.25rem; font-weight: 700; color: hsl(var(--primary));">${lot.occupancy_percent}%</div>
                </div>
            </div>
            <button class="btn btn-primary" style="width: 100%;" onclick='openBookingModal(${JSON.stringify(lot)})' ${lot.available_spots === 0 ? 'disabled style="opacity: 0.5; cursor: not-allowed;"' : ''}>
                ${lot.available_spots === 0 ? '❌ No Spots' : '🅿️ Book Parking →'}
            </button>
        </div>
    `}).join('');
}

// Open booking confirmation modal
function openBookingModal(lot) {
    selectedLot = typeof lot === 'string' ? JSON.parse(lot) : lot;

    // Reset duration
    const durationEl = document.getElementById('bookingDuration');
    durationEl.value = '1';
    bookingDuration = 1;

    // Update booking summary
    document.getElementById('modalLotName').textContent = selectedLot.name;
    document.getElementById('modalLotAddress').textContent = `${selectedLot.address}, ${selectedLot.city}`;

    // Show dynamic rate
    const isSurge = selectedLot.price_multiplier > 1;
    if (isSurge) {
        document.getElementById('modalHourlyRate').innerHTML = `
            <span style="text-decoration: line-through; color: hsl(var(--muted-foreground)); font-size: 0.875rem;">₹${selectedLot.base_rate}</span><br>
            <span style="color: hsl(var(--destructive)); font-weight: 700;">₹${selectedLot.dynamic_rate}/hr</span>
            <span style="font-size: 0.75rem; color: hsl(var(--destructive));">(${selectedLot.price_multiplier}x surge)</span>
        `;
    } else {
        document.getElementById('modalHourlyRate').textContent = `₹${selectedLot.dynamic_rate || selectedLot.hourly_rate}/hr`;
    }

    document.getElementById('modalAvailableSpots').textContent = `${selectedLot.available_spots} spots (${selectedLot.occupancy_percent}% full)`;
    
    // Initial pricing
    updatePricingDisplay();

    // Populate vehicle dropdown
    populateVehicleDropdown();

    // Reset vehicle selection
    document.getElementById('modalVehicleNumber').value = '';

    // Clear alerts
    document.getElementById('modalAlert').innerHTML = '';

    // Populate vehicles
    const vehicleSelect = document.getElementById('modalVehicleNumber');
    if (vehicleSelect) {
        const savedVehicles = JSON.parse(localStorage.getItem('savedVehicles') || '[]');
        if (savedVehicles.length > 0) {
            vehicleSelect.innerHTML = savedVehicles.map(v => `<option value="${v.number}">${v.number}</option>`).join('');
            document.getElementById('vehicleHint').style.display = 'none';
        } else {
            apiCall('/users/me').then(profile => {
                if (profile.vehicle_number) {
                    vehicleSelect.innerHTML = `<option value="${profile.vehicle_number}">${profile.vehicle_number}</option>`;
                    document.getElementById('vehicleHint').style.display = 'none';
                } else {
                    vehicleSelect.innerHTML = '<option value="">-- No vehicles found --</option>';
                    document.getElementById('vehicleHint').style.display = 'block';
                }
            }).catch(() => {});
        }
    }

    // Render cards if any
    const savedCardContainer = document.getElementById('savedCardOptions');
    if (savedCardContainer) {
        const savedCards = JSON.parse(localStorage.getItem('savedCards') || '[]');
        if (savedCards.length > 0) {
            savedCardContainer.innerHTML = savedCards.map((c, i) => `
                <label style="display: flex; gap: var(--space-sm); align-items: center; margin-top: var(--space-sm);">
                    <input type="radio" name="selectedCard" value="${c.last4}" ${i===0?'checked':''}>
                    <span style="font-size: var(--font-size-sm);">Visa ending in •••• ${c.last4}</span>
                </label>
            `).join('');
            savedCardContainer.style.display = 'block';
        } else {
            savedCardContainer.innerHTML = '<div style="font-size: var(--font-size-xs); color: hsl(var(--muted-foreground)); margin-top: var(--space-xs);">No saved cards. <a href="profile.html">Add one</a></div>';
            savedCardContainer.style.display = 'block';
        }
    }

    // Fetch wallet balance
    const balanceEl = document.getElementById('modalWalletBalance');
    if (balanceEl) {
        const localBal = localStorage.getItem('walletBalance') || '0.00';
        balanceEl.textContent = `₹${parseFloat(localBal).toFixed(2)}`;
    }

    document.getElementById('bookingModal').classList.add('active');
}

// Close booking modal
function closeBookingModal() {
    document.getElementById('bookingModal').classList.remove('active');
    selectedLot = null;
    selectedSpotId = null;
    document.getElementById('modalAlert').innerHTML = '';
}

// Confirm booking
async function confirmBooking() {
    if (!selectedLot) return;

    const vehicleNumber = document.getElementById('modalVehicleNumber').value;
    if (!vehicleNumber) {
        document.getElementById('modalAlert').innerHTML = `
            <div class="alert alert-error">
                ⚠️ Please select a vehicle from the dropdown above, or add one in your Profile.
            </div>
        `;
        return;
    }
    const paymentMethod = document.querySelector('input[name="payment"]:checked').value;
    const duration = parseInt(document.getElementById('bookingDuration').value) || 1;

    // Validate vehicle selection
    if (!vehicleNumber) {
        document.getElementById('modalAlert').innerHTML = `
            <div class="alert alert-error">
                ⚠️ Please select a vehicle from your account to proceed with booking
            </div>
        `;
        return;
    }

    if (!paymentMethod) {
        document.getElementById('modalAlert').innerHTML = `
            <div class="alert alert-error">
                ⚠️ Please select a payment method
            </div>
        `;
        return;
    }

    const hourlyRate = selectedLot.dynamic_rate || selectedLot.hourly_rate;
    const totalCost = duration * hourlyRate;

    if (paymentMethod === 'upi' || paymentMethod === 'card') {
        if (paymentMethod === 'card') {
            const savedCards = JSON.parse(localStorage.getItem('savedCards') || '[]');
            if (savedCards.length === 0) {
                 document.getElementById('modalAlert').innerHTML = `
                    <div class="alert alert-error">
                        ⚠️ Please add a card in your Profile first, or choose another payment method.
                    </div>
                 `;
                 return;
            }
        }
        document.getElementById('rzpAmount').textContent = `₹${totalCost.toFixed(2)}`;
        document.getElementById('razorpayModal').classList.add('active');
        // Store current details for Razorpay callback
        window.currentPaymentDetails = { paymentMethod, vehicleNumber, duration, hourlyRate };
        return; 
    } else if (paymentMethod === 'wallet') {
        const balanceText = document.getElementById('modalWalletBalance').textContent;
        const balance = parseFloat(balanceText.replace('₹', '')) || 0;
        if (balance < totalCost) {
            document.getElementById('modalAlert').innerHTML = `
                <div class="alert alert-error">
                    ⚠️ Insufficient ParkHub Wallet balance. Please add funds or choose another payment method.
                </div>
            `;
            return;
        }
    }
    
    // Proceed with booking directly for wallet
    await completePaymentAndBook(paymentMethod, vehicleNumber, duration, hourlyRate);
}

function cancelRazorpayPayment() {
    document.getElementById('razorpayModal').classList.remove('active');
}

async function processRazorpaySuccess() {
    const details = window.currentPaymentDetails;
    if (!details) return cancelRazorpayPayment();
    
    // simulate payment processing delay
    const btns = document.querySelectorAll('#razorpayModal .btn');
    btns.forEach(b => { b.disabled = true; b.style.opacity = '0.7'; });
    
    setTimeout(async () => {
        await completePaymentAndBook(details.paymentMethod, details.vehicleNumber, details.duration, details.hourlyRate);
        btns.forEach(b => { b.disabled = false; b.style.opacity = '1'; });
    }, 1500);
}

async function completePaymentAndBook(paymentMethod = 'upi', vehicleNum = null, dur = null, rate = null) {
    let btnMsg = null;
    if (paymentMethod === 'wallet') {
        const btn = document.getElementById('confirmBookingBtn');
        btnMsg = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '⏳ Processing...';
    }

    try {
        const booking = await apiCall('/bookings', {
            method: 'POST',
            body: JSON.stringify({
                lot_id: selectedLot.id,
                spot_id: selectedSpotId,
                vehicle_number: vehicleNum,
                payment_method: paymentMethod,
                duration_hours: dur,
                hourly_rate: rate
            })
        });

        // Close modals
        if (paymentMethod === 'upi' || paymentMethod === 'card') {
            document.getElementById('razorpayModal').classList.remove('active');
        } else {
            const btn = document.getElementById('confirmBookingBtn');
            btn.disabled = false;
            if (btnMsg) btn.innerHTML = btnMsg;
        }
        closeBookingModal();
        
        // Show success modal
        document.getElementById('successBookingId').textContent = booking.id;
        document.getElementById('successLotName').textContent = selectedLot.name || 'Parking Spot';
        document.getElementById('successAmount').textContent = `₹${parseFloat(booking.total_cost || (dur * rate)).toFixed(2)}`;
        document.getElementById('bookingSuccessModal').classList.add('active');
        
        // If wallet, update local frontend representation just for UX
        if (paymentMethod === 'wallet') {
            const currentBalText = document.getElementById('modalWalletBalance').textContent;
            const currentBal = parseFloat(currentBalText.replace('₹', '')) || 0;
            const deduction = parseFloat(booking.total_cost || (dur * rate));
            const newBal = (currentBal - deduction).toFixed(2);
            document.getElementById('modalWalletBalance').textContent = `₹${newBal}`;
            localStorage.setItem('walletBalance', newBal);
            
            // Add wallet transaction to history
            let txs = JSON.parse(localStorage.getItem('walletTxs') || '[]');
            txs.unshift({
                id: 'BKNG' + booking.id,
                type: 'debit',
                amount: deduction,
                date: new Date().toISOString()
            });
            localStorage.setItem('walletTxs', JSON.stringify(txs));
        }

    } catch (error) {
        if (paymentMethod === 'upi' || paymentMethod === 'card') {
            alert(`❌ Payment/Booking failed: ${error.message}`);
            document.getElementById('razorpayModal').classList.remove('active');
        } else {
            document.getElementById('modalAlert').innerHTML = `
                <div class="alert alert-error">
                    ❌ ${error.message}
                </div>
            `;
            const btn = document.getElementById('confirmBookingBtn');
            btn.disabled = false;
            if (btnMsg) btn.innerHTML = btnMsg;
        }
    }
}

function closeSuccessModal() {
    document.getElementById('bookingSuccessModal').classList.remove('active');
    const bookingsTab = document.querySelector('[data-tab=bookings]');
    if (bookingsTab) bookingsTab.click();
}

// Payment option selection
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.payment-option').forEach(option => {
        option.addEventListener('click', function () {
            document.querySelectorAll('.payment-option').forEach(o => o.classList.remove('selected'));
            this.classList.add('selected');
            this.querySelector('input').checked = true;
        });
    });
});

// Load active bookings
async function loadActiveBookings() {
    const container = document.getElementById('activeBookingsContainer');

    try {
        const bookings = await apiCall('/bookings?status=ACTIVE');

        if (bookings.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🅿️</div>
                    <h3>No Active Bookings</h3>
                    <p>You don't have any active parking bookings right now</p>
                    <button class="btn btn-primary" style="margin-top: 1rem;" onclick="document.querySelector('[data-tab=search]').click()">
                        🔍 Search for Parking
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = bookings.map(booking => {
            const startTime = new Date(booking.start_time);
            const elapsed = getElapsedTime(booking.start_time);
            const duration = booking.duration_hours || 1;
            const hourlyRate = booking.hourly_rate || 0;
            const estimatedCost = duration * hourlyRate;
            
            return `
            <div class="booking-card">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                    <div>
                        <h3 style="font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem;">
                            📍 Spot ${booking.spot_id}
                        </h3>
                        <p style="color: hsl(var(--muted-foreground)); font-size: 0.875rem; margin-bottom: 0.5rem;">
                            Lot: ${booking.lot_id}
                        </p>
                        <p style="color: hsl(var(--muted-foreground)); font-size: 0.875rem; margin-bottom: 0.5rem;">
                            Started: ${startTime.toLocaleString()}
                        </p>
                        <p style="color: hsl(var(--muted-foreground)); font-size: 0.875rem; margin-bottom: 0.5rem;">
                            🚗 Vehicle: <strong>${booking.vehicle_number}</strong>
                        </p>
                        <p style="color: hsl(var(--primary)); font-size: 0.875rem; font-weight: 600;">
                            ⏱️ Duration: ${elapsed} of ${duration}h | 💰 ₹${estimatedCost.toFixed(2)}
                        </p>
                    </div>
                    <button class="btn btn-secondary" onclick="promptReleaseBooking(${booking.id})" style="padding: 0.5rem 1rem; font-size: 0.85rem; min-height: 2rem; white-space: nowrap;">
                        🛑 End Parking
                    </button>
                </div>
            </div>
        `}).join('');
    } catch (error) {
        container.innerHTML = `
            <div style="background: hsl(var(--destructive) / 0.1); border: 1px solid hsl(var(--destructive)); border-radius: var(--radius); padding: var(--space-lg);">
                <p style="color: hsl(var(--destructive));">Error loading active bookings: ${error.message}</p>
            </div>
        `;
    }
}

// Calculate elapsed time
function getElapsedTime(startTime) {
    const start = new Date(startTime);
    const now = new Date();
    const diff = Math.floor((now - start) / 1000 / 60); // minutes

    if (diff < 60) return `${diff}m`;
    const hours = Math.floor(diff / 60);
    const mins = diff % 60;
    return `${hours}h ${mins}m`;
}

window.pendingReleaseBookingId = null;

// Release booking flow
function promptReleaseBooking(bookingId) {
    window.pendingReleaseBookingId = bookingId;
    document.getElementById('endBookingConfirmModal').classList.add('active');
}

function cancelReleaseBooking() {
    window.pendingReleaseBookingId = null;
    document.getElementById('endBookingConfirmModal').classList.remove('active');
}

async function confirmReleaseBooking() {
    if (!window.pendingReleaseBookingId) return;
    
    document.getElementById('endBookingConfirmModal').classList.remove('active');
    
    try {
        await apiCall(`/bookings/${window.pendingReleaseBookingId}/release`, { method: 'POST' });
        
        showAlert('✅ Parking session ended successfully.', 'success');
        
        setTimeout(() => {
            loadActiveBookings();
            loadBookingHistory();
        }, 1500);
        
    } catch (error) {
        showAlert(`❌ Failed to end parking: ${error.message}`, 'error');
    } finally {
        window.pendingReleaseBookingId = null;
    }
}

// Load booking history
async function loadBookingHistory() {
    const container = document.getElementById('historyContainer');

    try {
        const bookings = await apiCall('/bookings?status=COMPLETED');

        if (bookings.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📋</div>
                    <h3>No Booking History</h3>
                    <p>Your completed parking bookings will appear here</p>
                </div>
            `;
            return;
        }

        container.innerHTML = bookings.map(booking => {
            const startTime = new Date(booking.start_time);
            const duration = booking.duration_hours || 1;
            const hourlyRate = booking.hourly_rate || 0;
            const cost = parseFloat(booking.total_cost || 0) || (duration * hourlyRate);
            
            return `
            <div class="booking-card">
                <div style="display: grid; grid-template-columns: 1fr auto; gap: 1rem;">
                    <div>
                        <h3 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 0.5rem;">
                            📍 Spot ${booking.spot_id}
                        </h3>
                        <p style="color: hsl(var(--muted-foreground)); font-size: 0.875rem; margin-bottom: 0.25rem;">
                            📅 ${startTime.toLocaleDateString()} ${startTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                        <p style="color: hsl(var(--muted-foreground)); font-size: 0.875rem; margin-bottom: 0.25rem;">
                            🚗 ${booking.vehicle_number}
                        </p>
                        <p style="color: hsl(var(--muted-foreground)); font-size: 0.875rem;">
                            ⏱️ Duration: ${duration}h
                        </p>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 2rem; font-weight: 700; color: hsl(var(--primary));">₹${cost.toFixed(2)}</div>
                        <div style="font-size: 0.875rem; color: hsl(var(--muted-foreground));">Paid</div>
                    </div>
                </div>
            </div>
        `}).join('');
    } catch (error) {
        container.innerHTML = `
            <div style="background: hsl(var(--destructive) / 0.1); border: 1px solid hsl(var(--destructive)); border-radius: var(--radius); padding: var(--space-lg);">
                <p style="color: hsl(var(--destructive));">Error loading booking history: ${error.message}</p>
            </div>
        `;
    }
}

// Show alert notifications
function showAlert(message, type = 'info') {
    let alertContainer = document.querySelector('.alert-container');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.className = 'alert-container';
        alertContainer.style.position = 'fixed';
        alertContainer.style.top = '80px';
        alertContainer.style.right = '20px';
        alertContainer.style.zIndex = '999';
        document.body.appendChild(alertContainer);
    }

    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    alert.style.marginBottom = '10px';
    alert.style.animation = 'slideIn 0.3s ease';
    
    alertContainer.appendChild(alert);

    setTimeout(() => alert.remove(), 4000);
}

// Tab switching
document.addEventListener('DOMContentLoaded', () => {
    // Load user vehicles on page load
    if (checkAuth()) {
        loadUserVehicles();
        loadParkingLots();
        loadActiveBookings();
        loadBookingHistory();
    }

    // Tab switching functionality
    document.querySelectorAll('.dashboard-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            
            document.querySelectorAll('.dashboard-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');

            if (tabName === 'bookings') {
                loadActiveBookings();
            } else if (tabName === 'history') {
                loadBookingHistory();
            }
        });
    });

    // Search form
    const searchBtn = document.getElementById('searchBtn');
    if (searchBtn) {
        searchBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const location = document.getElementById('searchLocation').value;
            const pinCode = document.getElementById('searchPinCode').value;
            loadParkingLots(location, pinCode);
        });
    }

    // Add CSS for animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(400px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
    `;
    document.head.appendChild(style);
});
