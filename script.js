// Menu Data
const MENU_ITEMS = [
    {
        id: 1,
        name: "The Beastly Burger",
        description: "Double Wagyu beef, truffle aioli, aged cheddar, and crispy bacon on a brioche bun.",
        price: 18.99,
        category: 'Burgers',
        image: "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&q=80&w=800"
    },
    {
        id: 2,
        name: "Wild Wings",
        description: "Crispy chicken wings tossed in our signature spicy buffalo sauce.",
        price: 12.50,
        category: 'Appetizers',
        image: "https://images.unsplash.com/photo-1608039829572-78524f79c4c7?auto=format&fit=crop&q=80&w=800"
    },
    {
        id: 3,
        name: "Apex Steak",
        description: "12oz Prime Ribeye served with garlic mashed potatoes and grilled asparagus.",
        price: 34.00,
        category: 'Main Course',
        image: "https://images.unsplash.com/photo-1546241072-48010ad28c2c?auto=format&fit=crop&q=80&w=800"
    },
    {
        id: 4,
        name: "Predator Pasta",
        description: "Spicy Italian sausage, sun-dried tomatoes, and spinach in a creamy vodka sauce.",
        price: 21.00,
        category: 'Main Course',
        image: "https://images.unsplash.com/photo-1563379926898-05f4575a45d8?auto=format&fit=crop&q=80&w=800"
    },
    {
        id: 5,
        name: "Truffle Fries",
        description: "Hand-cut fries tossed with truffle oil, parmesan, and fresh parsley.",
        price: 8.50,
        category: 'Appetizers',
        image: "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?auto=format&fit=crop&q=80&w=800"
    },
    {
        id: 6,
        name: "Volcano Cake",
        description: "Warm chocolate lava cake with vanilla bean ice cream.",
        price: 9.99,
        category: 'Desserts',
        image: "https://images.unsplash.com/photo-1624353339193-29b315d85642?auto=format&fit=crop&q=80&w=800"
    },
    {
        id: 7,
        name: "Monster Milkshake",
        description: "Giant Oreo and brownie milkshake topped with whipped cream.",
        price: 7.50,
        category: 'Drinks',
        image: "https://images.unsplash.com/photo-1572490122747-3968b75cc699?auto=format&fit=crop&q=80&w=800"
    },
    {
        id: 8,
        name: "Dragon's Breath",
        description: "Spicy mango and habanero infused mocktail with a chili rim.",
        price: 6.50,
        category: 'Drinks',
        image: "https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b?auto=format&fit=crop&q=80&w=800"
    }
];

// App State
let cart = [];
let activeSection = 'home';

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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    renderMenu();
    setupNavigation();
    setupCartListeners();
    setupFormListeners();
    animateCounters(); // Initialize scroll observer
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

    document.getElementById('explore-menu').addEventListener('click', () => switchSection('menu'));
    document.getElementById('home-link').addEventListener('click', () => switchSection('home'));
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
        
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
            resStatus.innerHTML = `<div class="info-group" style="margin-top: 20px; border-color: #22c55e;">
                <i class="fas fa-check-circle" style="color: #22c55e;"></i>
                <div>
                    <h4 style="color: #22c55e;">Reservation Confirmed!</h4>
                    <p>The pack is ready for you. We'll text a confirmation to ${document.getElementById('res-phone').value}.</p>
                </div>
            </div>`;
            resForm.reset();
            
            // Auto hide status after 5 seconds
            setTimeout(() => {
                resStatus.innerHTML = '';
            }, 5000);
        }, 2000);
    });
}



function switchSection(sectionId) {
    sections.forEach(s => s.classList.remove('active'));
    document.getElementById(sectionId).classList.add('active');
    
    navLinks.forEach(l => {
        l.classList.remove('active');
        if (l.getAttribute('data-section') === sectionId) l.classList.add('active');
    });
    
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Counter animation trigger removed from here to support scroll-based trigger
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
                <div class="price-tag">$${item.price.toFixed(2)}</div>
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
                        <span class="accent">$${(item.price * item.quantity).toFixed(2)}</span>
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
    const delivery = subtotal > 0 ? 5.00 : 0;
    subtotalEl.textContent = `$${subtotal.toFixed(2)}`;
    document.getElementById('delivery-fee').textContent = `$${delivery.toFixed(2)}`;
    totalPriceEl.textContent = `$${(subtotal + delivery).toFixed(2)}`;
}

// Cart UI
function setupCartListeners() {
    document.getElementById('cart-open').addEventListener('click', openCart);
    document.getElementById('cart-close').addEventListener('click', closeCart);
    cartOverlay.addEventListener('click', closeCart);
    
    document.getElementById('place-order').addEventListener('click', () => {
        if (cart.length === 0) return;
        
        const btn = document.getElementById('place-order');
        btn.disabled = true;
        btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Placing Order...`;
        
        setTimeout(() => {
            orderStatus.innerHTML = `<i class="fas fa-check-circle" style="color: #22c55e;"></i> Order Placed! The beast is on its way.`;
            cart = [];
            updateCart();
            
            setTimeout(() => {
                orderStatus.innerHTML = '';
                btn.disabled = false;
                btn.innerHTML = `Place Order <i class="fas fa-chevron-right"></i>`;
                closeCart();
            }, 3000);
        }, 2000);
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
