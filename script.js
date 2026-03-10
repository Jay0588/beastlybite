// Menu Data
const MENU_ITEMS = [
    {
        id: 1,
        name: "The Beastly Burger",
        description: "Double Wagyu beef, truffle aioli, aged cheddar, and crispy bacon on a brioche bun.",
        price: 499,
        category: 'Burgers',
        image: "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&q=80&w=800"
    },
    {
        id: 2,
        name: "Wild Wings",
        description: "Crispy chicken wings tossed in our signature spicy buffalo sauce.",
        price: 349,
        category: 'Appetizers',
        image: "https://images.unsplash.com/photo-1608039829572-78524f79c4c7?auto=format&fit=crop&q=80&w=800"
    },
    {
        id: 3,
        name: "Apex Steak",
        description: "12oz Prime Ribeye served with garlic mashed potatoes and grilled asparagus.",
        price: 1299,
        category: 'Main Course',
        image: "https://images.unsplash.com/photo-1546241072-48010ad28c2c?auto=format&fit=crop&q=80&w=800"
    },
    {
        id: 4,
        name: "Predator Pasta",
        description: "Spicy Italian sausage, sun-dried tomatoes, and spinach in a creamy vodka sauce.",
        price: 599,
        category: 'Main Course',
        image: "https://images.unsplash.com/photo-1563379926898-05f4575a45d8?auto=format&fit=crop&q=80&w=800"
    },
    {
        id: 5,
        name: "Truffle Fries",
        description: "Hand-cut fries tossed with truffle oil, parmesan, and fresh parsley.",
        price: 249,
        category: 'Appetizers',
        image: "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?auto=format&fit=crop&q=80&w=800"
    },
    {
        id: 6,
        name: "Volcano Cake",
        description: "Warm chocolate lava cake with vanilla bean ice cream.",
        price: 299,
        category: 'Desserts',
        image: "https://images.unsplash.com/photo-1624353339193-29b315d85642?auto=format&fit=crop&q=80&w=800"
    },
    {
        id: 7,
        name: "Monster Milkshake",
        description: "Giant Oreo and brownie milkshake topped with whipped cream.",
        price: 199,
        category: 'Drinks',
        image: "https://images.unsplash.com/photo-1572490122747-3968b75cc699?auto=format&fit=crop&q=80&w=800"
    },
    {
        id: 8,
        name: "Dragon's Breath",
        description: "Spicy mango and habanero infused mocktail with a chili rim.",
        price: 149,
        category: 'Drinks',
        image: "https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b?auto=format&fit=crop&q=80&w=800"
    }
];

// App State
let cart = [];
let activeSection = 'home';
let orders = JSON.parse(localStorage.getItem('beastly_orders')) || [];
let reservations = JSON.parse(localStorage.getItem('beastly_reservations')) || [];

// DOM Elements
const menuGrid = document.getElementById('menu-grid');
const cartItemsContainer = document.getElementById('cart-items');
const cartCount = document.querySelectorAll('.cart-count');
const subtotalEl = document.getElementById('subtotal');
const totalPriceEl = document.getElementById('total-price');
const cartSidebar = document.getElementById('cart-sidebar');
const cartOverlay = document.getElementById('cart-overlay');
const sections = document.querySelectorAll('.section');
const navLinks = document.querySelectorAll('.nav-links a');
const orderStatus = document.getElementById('order-status');
const mobileToggle = document.getElementById('mobile-toggle');
const mobileMenuOverlay = document.getElementById('mobile-menu-overlay');
const mobileMenuClose = document.getElementById('mobile-menu-close');
const mobileNavLinks = document.querySelectorAll('.mobile-nav-links a');

// Checkout Elements
const checkoutForm = document.getElementById('checkout-form');
const upiDetails = document.getElementById('upi-details');
const checkoutItemsList = document.getElementById('checkout-items-list');
const chkSubtotal = document.getElementById('chk-subtotal');
const chkDelivery = document.getElementById('chk-delivery');
const chkTotal = document.getElementById('chk-total');

// Payment Modal Elements
const paymentModal = document.getElementById('payment-modal');
const pmClose = document.getElementById('pm-close');
const pmPayBtn = document.getElementById('pm-pay-btn');
const pmTotalAmount = document.getElementById('pm-total-amount');
const pmBtnAmount = document.getElementById('pm-btn-amount');
const pmOrderId = document.getElementById('pm-order-id');

// Admin Elements
const ordersListBody = document.getElementById('orders-list-body');
const reservationsListBody = document.getElementById('reservations-list-body');
const totalOrdersCount = document.getElementById('total-orders-count');
const totalRevenueCount = document.getElementById('total-revenue-count');
const pendingOrdersCount = document.getElementById('pending-orders-count');

// Order Success Elements
const successOrderId = document.getElementById('success-order-id');
const successTotal = document.getElementById('success-total');
const successPayment = document.getElementById('success-payment');
const successItemsList = document.getElementById('success-items-list');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    renderMenu();
    setupNavigation();
    setupCartListeners();
    setupFormListeners();
    animateCounters(); // Initialize scroll observer
    setupMobileMenu();
    setupCheckout();
    setupPaymentModal();
    renderAdminDashboard();
});

// Navigation
function setupNavigation() {
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const sectionId = link.getAttribute('data-section');
            if (sectionId) switchSection(sectionId);
        });
    });

    mobileNavLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const sectionId = link.getAttribute('data-section');
            if (sectionId) {
                switchSection(sectionId);
                closeMobileMenu();
            }
        });
    });

    document.getElementById('explore-menu').addEventListener('click', () => switchSection('menu'));
    document.getElementById('home-link').addEventListener('click', () => {
        switchSection('home');
    });
}

function setupMobileMenu() {
    mobileToggle.addEventListener('click', openMobileMenu);
    mobileMenuClose.addEventListener('click', closeMobileMenu);
}

function openMobileMenu() {
    mobileMenuOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeMobileMenu() {
    mobileMenuOverlay.classList.remove('active');
    document.body.style.overflow = 'auto';
}


// Form Listeners
function setupFormListeners() {
    // Reservation Form
    const resForm = document.getElementById('reservation-form');
    const resStatus = document.getElementById('reservation-status');

    resForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const btn = resForm.querySelector('button');
        const originalText = btn.innerHTML;
        
        btn.disabled = true;
        btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Checking Availability...`;
        
        const reservationData = {
            id: 'RES' + Math.floor(Math.random() * 1000000),
            name: document.getElementById('res-name').value,
            phone: document.getElementById('res-phone').value,
            date: document.getElementById('res-date').value,
            time: document.getElementById('res-time').value,
            guests: document.getElementById('res-guests').value,
            occasion: document.getElementById('res-occasion').value,
            notes: document.getElementById('res-notes').value,
            timeBooked: new Date().toLocaleString()
        };

        setTimeout(() => {
            // Save to reservations array and localStorage
            reservations.unshift(reservationData);
            localStorage.setItem('beastly_reservations', JSON.stringify(reservations));

            btn.innerHTML = originalText;
            btn.disabled = false;
            resStatus.innerHTML = `<div class="info-group" style="margin-top: 20px; border-color: #22c55e;">
                <i class="fas fa-check-circle" style="color: #22c55e;"></i>
                <div>
                    <h4 style="color: #22c55e;">Reservation Confirmed!</h4>
                    <p>The pack is ready for you. We'll text a confirmation to ${reservationData.phone}.</p>
                </div>
            </div>`;
            resForm.reset();
            
            // Auto hide status after 5 seconds
            setTimeout(() => {
                resStatus.innerHTML = '';
            }, 5000);
            
            renderAdminDashboard();
        }, 2000);
    });
}



function switchSection(sectionId) {
    const currentActive = document.querySelector('.section.active');
    if (currentActive) {
        currentActive.classList.remove('active');
    }

    setTimeout(() => {
        sections.forEach(s => s.style.display = 'none');
        const newActive = document.getElementById(sectionId);
        newActive.style.display = 'block';
        setTimeout(() => newActive.classList.add('active'), 50); // Delay to trigger transition
    }, 250); // Half of the transition time

    navLinks.forEach(l => {
        l.classList.remove('active');
        if (l.getAttribute('data-section') === sectionId) l.classList.add('active');
    });
    
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Counter animation for About section
    if (sectionId === 'about') {
        animateCounters();
    }

    // Prepare checkout if moving to it
    if (sectionId === 'checkout') {
        prepareCheckout();
    }

    // Refresh Admin Dashboard if moving to it
    if (sectionId === 'admin') {
        renderAdminDashboard();
    }
}

function setupCheckout() {
    // Set initial state
    const confirmBtn = document.getElementById('confirm-checkout');
    if (document.querySelector('input[name="payment"]:checked').value === 'razorpay') {
        upiDetails.style.display = 'block';
        confirmBtn.style.background = '#3B82F6';
        confirmBtn.style.borderColor = '#3B82F6';
    } else {
        upiDetails.style.display = 'none';
    }

    // Payment method toggle
    const paymentOptions = document.querySelectorAll('input[name="payment"]');
    paymentOptions.forEach(opt => {
        opt.addEventListener('change', (e) => {
            const confirmBtn = document.getElementById('confirm-checkout');
            if (e.target.value === 'razorpay') {
                upiDetails.style.display = 'block';
                confirmBtn.style.background = '#3B82F6';
                confirmBtn.style.borderColor = '#3B82F6';
            } else {
                upiDetails.style.display = 'none';
                confirmBtn.style.background = '';
                confirmBtn.style.borderColor = '';
            }
        });
    });

    // Checkout Form Submit
    if (checkoutForm) {
        checkoutForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const paymentMethod = document.querySelector('input[name="payment"]:checked').value;
            
            if (paymentMethod === 'razorpay') {
                // Show Razorpay-like Modal
                const total = chkTotal.textContent;
                const tempId = 'order_' + Math.random().toString(36).substr(2, 9);
                pmOrderId.textContent = tempId;
                pmTotalAmount.textContent = total;
                paymentModal.style.display = 'flex';
            } else {
                // Cash on Delivery - Save immediately
                processOrder('COD');
            }
        });
    }
}

function setupPaymentModal() {
    pmClose.addEventListener('click', () => {
        paymentModal.style.display = 'none';
    });

    pmPayBtn.addEventListener('click', () => {
        pmPayBtn.disabled = true;
        pmPayBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Processing...`;
        
        setTimeout(() => {
            pmPayBtn.disabled = false;
            pmPayBtn.innerHTML = `Pay Now`;
            paymentModal.style.display = 'none';
            processOrder('Razorpay', pmOrderId.textContent);
        }, 2500);
    });
}

function processOrder(method, existingId = null) {
    const btn = document.getElementById('confirm-checkout');
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Finalizing Order...`;
    
    setTimeout(() => {
        const orderData = {
            id: existingId || ('ORD' + Math.floor(Math.random() * 1000000)),
            customer: document.getElementById('chk-name').value,
            phone: document.getElementById('chk-phone').value,
            address: document.getElementById('chk-address').value,
            city: document.getElementById('chk-city').value,
            items: cart.map(i => `${i.quantity}x ${i.name}`).join(', '),
            total: chkTotal.textContent,
            payment: method,
            time: new Date().toLocaleString(),
            status: method === 'Razorpay' ? 'Paid' : 'COD'
        };

        // Save to orders array and localStorage
        orders.unshift(orderData);
        localStorage.setItem('beastly_orders', JSON.stringify(orders));

        // Populate and show success page
        successOrderId.textContent = orderData.id;
        successTotal.textContent = orderData.total;
        successPayment.textContent = orderData.payment;
        successItemsList.innerHTML = cart.map(item => `
            <div class="chk-item-row">
                <span><span class="qty">${item.quantity}x</span> ${item.name}</span>
                <span>₹${(item.price * item.quantity).toFixed(2)}</span>
            </div>
        `).join('');
        switchSection('order-success');

        cart = [];
        updateCart();
        checkoutForm.reset();
        renderAdminDashboard();
    }, 1500);
}

function renderAdminDashboard() {
    if (!ordersListBody) return;

    // Update Stats
    totalOrdersCount.textContent = orders.length;
    const revenue = orders.reduce((acc, order) => {
        const amount = parseFloat(order.total.split('₹')[1]);
        return acc + amount;
    }, 0);
    totalRevenueCount.textContent = `₹${revenue.toFixed(2)}`;
    pendingOrdersCount.textContent = orders.filter(o => o.status === 'COD').length;

    // Render Orders Table
    if (orders.length === 0) {
        ordersListBody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 50px; color: var(--text-secondary);">No orders yet. Start hunting!</td></tr>`;
    } else {
        ordersListBody.innerHTML = orders.map(order => `
            <tr>
                <td style="font-weight: bold; color: var(--accent-color);">${order.id}</td>
                <td>
                    <div style="font-weight: bold;">${order.customer}</div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary);">${order.phone}</div>
                </td>
                <td>
                    <div style="font-size: 0.8rem; line-height: 1.2;">${order.address}, ${order.city}</div>
                </td>
                <td style="max-width: 150px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${order.items}">${order.items}</td>
                <td style="font-weight: bold;">${order.total}</td>
                <td>${order.payment}</td>
                <td style="font-size: 0.75rem; color: var(--text-secondary);">${order.time}</td>
                <td>
                    <span class="status-badge ${order.status.toLowerCase()}">${order.status}</span>
                </td>
            </tr>
        `).join('');
    }

    // Render Reservations Table
    if (!reservationsListBody) return;
    if (reservations.length === 0) {
        reservationsListBody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 50px; color: var(--text-secondary);">No reservations yet.</td></tr>`;
    } else {
        reservationsListBody.innerHTML = reservations.map(res => `
            <tr>
                <td style="font-weight: bold; color: var(--accent-color);">${res.id}</td>
                <td>
                    <div style="font-weight: bold;">${res.name}</div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary);">${res.phone}</div>
                </td>
                <td>
                    <div style="font-weight: bold;">${res.date}</div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary);">${res.time}</div>
                </td>
                <td>${res.guests}</td>
                <td style="text-transform: capitalize;">${res.occasion}</td>
                <td style="max-width: 150px; font-size: 0.8rem; color: var(--text-secondary);">${res.notes || 'No notes'}</td>
                <td style="font-size: 0.75rem; color: var(--text-secondary);">${res.timeBooked}</td>
            </tr>
        `).join('');
    }
}

function clearAllOrders() {
    if (confirm("Are you sure you want to clear all order history? This cannot be undone.")) {
        orders = [];
        localStorage.removeItem('beastly_orders');
        renderAdminDashboard();
    }
}

function clearAllReservations() {
    if (confirm("Are you sure you want to clear all reservation history? This cannot be undone.")) {
        reservations = [];
        localStorage.removeItem('beastly_reservations');
        renderAdminDashboard();
    }
}

function prepareCheckout() {
    if (cart.length === 0) {
        alert("Your haul is empty! Go hunting in the menu first.");
        switchSection('menu');
        return;
    }

    // Render summary
    checkoutItemsList.innerHTML = cart.map(item => `
        <div class="chk-item-row">
            <span><span class="qty">${item.quantity}x</span> ${item.name}</span>
            <span>₹${(item.price * item.quantity).toFixed(2)}</span>
        </div>
    `).join('');

    const subtotal = cart.reduce((acc, item) => acc + (item.price * item.quantity), 0);
    const delivery = 40.00;
    
    chkSubtotal.textContent = `₹${subtotal.toFixed(2)}`;
    chkDelivery.textContent = `₹${delivery.toFixed(2)}`;
    chkTotal.textContent = `₹${(subtotal + delivery).toFixed(2)}`;
}

function animateCounters() {
    const counters = document.querySelectorAll('.counter');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const counter = entry.target;
                startCounting(counter);
                observer.unobserve(counter); // Only animate once
            }
        });
    }, { threshold: 0.5 });

    counters.forEach(counter => {
        observer.observe(counter);
    });
}

function startCounting(counter) {
    const target = parseInt(counter.getAttribute('data-target'));
    const suffix = counter.getAttribute('data-suffix') || '';
    const duration = 2000; // 2 seconds animation
    const startTime = performance.now();
    
    const updateCount = (currentTime) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function (easeOutExpo)
        const easedProgress = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
        
        const currentCount = Math.floor(easedProgress * target);
        counter.textContent = currentCount + suffix;
        
        if (progress < 1) {
            requestAnimationFrame(updateCount);
        } else {
            counter.textContent = target + suffix;
        }
    };
    
    requestAnimationFrame(updateCount);
}



// Menu Rendering
function renderMenu() {
    menuGrid.innerHTML = MENU_ITEMS.map(item => `
        <div class="menu-item">
            <div class="menu-img">
                <img src="${item.image}" alt="${item.name}">
                <div class="price-tag">₹${item.price.toFixed(2)}</div>
            </div>
            <div class="menu-info">
                <div class="category">${item.category}</div>
                <h3>${item.name}</h3>
                <p>${item.description}</p>
                <button class="btn btn-primary btn-block" onclick="addToCart(${item.id})">
                    <i class="fas fa-plus"></i> Add to Cart
                </button>
            </div>
        </div>
    `).join('');
}

// Cart Logic
function addToCart(id) {
    const item = MENU_ITEMS.find(i => i.id === id);
    const existing = cart.find(i => i.id === id);

    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({ ...item, quantity: 1 });
    }

    updateCart();
    openCart();
}

function removeFromCart(id) {
    cart = cart.filter(i => i.id !== id);
    updateCart();
}

function updateQuantity(id, delta) {
    const item = cart.find(i => i.id === id);
    if (item) {
        item.quantity += delta;
        if (item.quantity <= 0) {
            removeFromCart(id);
        } else {
            updateCart();
        }
    }
}

function updateCart() {
    // Update Count
    const count = cart.reduce((acc, item) => acc + item.quantity, 0);
    cartCount.forEach(el => el.textContent = count);

    // Render Items
    if (cart.length === 0) {
        cartItemsContainer.innerHTML = `
            <div style="text-align: center; padding: 50px 0; color: #475569;">
                <i class="fas fa-shopping-basket" style="font-size: 3rem; margin-bottom: 20px;"></i>
                <p>Your haul is empty</p>
            </div>
        `;
    } else {
        cartItemsContainer.innerHTML = cart.map(item => `
            <div class="cart-item">
                <img src="${item.image}" class="cart-item-img" alt="${item.name}">
                <div class="cart-item-info">
                    <div class="cart-item-header">
                        <h4>${item.name}</h4>
                        <span class="accent">₹${(item.price * item.quantity).toFixed(2)}</span>
                    </div>
                    <div class="cart-item-controls">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <button class="qty-btn" onclick="updateQuantity(${item.id}, -1)">-</button>
                            <span style="font-weight: bold; font-size: 0.9rem;">${item.quantity}</span>
                            <button class="qty-btn" onclick="updateQuantity(${item.id}, 1)">+</button>
                        </div>
                        <button class="remove-btn" onclick="removeFromCart(${item.id})">Remove</button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // Update Totals
    const subtotal = cart.reduce((acc, item) => acc + (item.price * item.quantity), 0);
    const delivery = subtotal > 0 ? 40.00 : 0;
    subtotalEl.textContent = `₹${subtotal.toFixed(2)}`;
    document.getElementById('delivery-fee').textContent = `₹${delivery.toFixed(2)}`;
    totalPriceEl.textContent = `₹${(subtotal + delivery).toFixed(2)}`;
}

// Cart UI
function setupCartListeners() {
    document.getElementById('cart-open').addEventListener('click', openCart);
    document.getElementById('cart-close').addEventListener('click', closeCart);
    cartOverlay.addEventListener('click', closeCart);
    
    document.getElementById('place-order').addEventListener('click', () => {
        if (cart.length === 0) return;
        closeCart();
        switchSection('checkout');
    });
}

function openCart() {
    cartSidebar.classList.add('active');
    cartOverlay.style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function closeCart() {
    cartSidebar.classList.remove('active');
    cartOverlay.style.display = 'none';
    document.body.style.overflow = 'auto';
}
