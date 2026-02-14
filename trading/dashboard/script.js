let cachedData = null;
let currentCoin = 'BTC';

function updateActiveTrades(data) {
    const container = document.getElementById('active-trades');
    
    const signals = data.signals || [];
    const prices = data.prices || {};
    const strategies = data.strategies || [];
    const BUYIN = 100; // $100 per trade
    
    if (signals.length === 0) {
        container.innerHTML = '<div class="no-trades">Keine Trades</div>';
        return;
    }

    // Sort by date descending (newest first)
    signals.sort((a, b) => new Date(b.date) - new Date(a.date));
    
    container.innerHTML = signals.map(sig => {
        const isOpen = sig.status === 'ACTIVE';
        const currentPrice = prices[sig.symbol] || 0;
        const entryPrice = sig.entry || 0;
        const diff = currentPrice - entryPrice;
        
        // Calculate P/L with $100 buyin
        const positionSize = BUYIN / entryPrice; // how many coins
        const profitDollar = positionSize * diff;
        const pct = entryPrice > 0 ? ((diff / entryPrice) * 100) : 0;
        const isProfit = diff >= 0;
        
        // Format date
        const tradeDate = sig.date ? new Date(sig.date).toLocaleDateString('de-DE') : '-';
        
        return `
            <div class="trade-card ${isOpen ? (isProfit ? 'profit' : 'loss') : (isProfit ? 'profit-closed' : 'loss-closed')}">
                <div class="trade-header">
                    <span class="trade-symbol">${sig.symbol}</span>
                    <span class="trade-type ${sig.signal.toLowerCase()}">${sig.signal}${!isOpen ? ' ✕' : ''}</span>
                </div>
                <div class="trade-date">📅 ${tradeDate}</div>
                <div class="trade-prices">
                    <div class="trade-row">
                        <span>Entry</span>
                        <span class="mono">$${entryPrice.toLocaleString()}</span>
                    </div>
                    ${isOpen ? `
                    <div class="trade-row">
                        <span>Jetzt</span>
                        <span class="mono">$${currentPrice.toLocaleString()}</span>
                    </div>
                    ` : ''}
                    <div class="trade-row">
                        <span>P/L (${BUYIN}$)</span>
                        <span class="mono ${isProfit ? 'green' : 'red'}">
                            ${isProfit ? '+' : ''}${profitDollar.toFixed(2)}$ (${isProfit ? '+' : ''}${pct.toFixed(2)}%)
                        </span>
                    </div>
                </div>
                <div class="trade-sl-tp">
                    <span>SL: $${(sig.sl || 0).toLocaleString()}</span>
                    <span>TP: $${(sig.tp || 0).toLocaleString()}</span>
                </div>
            </div>
        `;
    }).join('');
}

async function updateDashboard() {
    try {
        const response = await fetch('data.json');
        const data = await response.json();
        cachedData = data;

        // Update Global Stats
        document.getElementById('db-size').innerText = data.db_size;
        document.getElementById('last-sync').innerText = data.last_sync;

        // Update Prices
        for (const [coin, price] of Object.entries(data.prices)) {
            const el = document.getElementById(`price-${coin}`);
            if (el) {
                const formattedPrice = price.toLocaleString('en-US', { minimumFractionDigits: 2 });
                el.innerText = `$${formattedPrice}`;
            }
        }

        // Update Active Trades Panel
        updateActiveTrades(data);

        // Update Signal Banner - Today's Trades
        const banner = document.getElementById('signal-banner');
        const bannerText = document.getElementById('signal-text');
        
        // Filter today's trades
        const today = new Date().toISOString().split('T')[0];
        const todaySignals = data.signals.filter(s => s.date && s.date.startsWith(today));
        
        if (todaySignals.length > 0) {
            banner.classList.remove('hidden');
            
            if (todaySignals.length === 1) {
                // Single trade - show normally
                const s = todaySignals[0];
                bannerText.innerHTML = `<span class="banner-trade"><span class="iconify" data-icon="ant-design:stock-outlined"></span> ${s.symbol} ${s.signal} @ $${s.entry?.toLocaleString()}</span>`;
            } else {
                // Multiple trades - show as marquee
                const tradesHtml = todaySignals.map(s => 
                    `<span class="banner-trade"><span class="iconify" data-icon="ant-design:stock-outlined"></span> ${s.symbol} ${s.signal} @ $${s.entry?.toLocaleString()}</span>`
                ).join('<span class="banner-sep">•••</span>');
                bannerText.innerHTML = `<div class="banner-marquee"><div class="banner-marquee-inner">${tradesHtml}${tradesHtml}</div></div>`;
            }
        } else {
            banner.classList.add('hidden');
        }

        // Update Strategies
        const stratList = document.getElementById('strategy-list');
        stratList.innerHTML = '';
        data.strategies.forEach(strat => {
            const card = document.createElement('div');
            card.className = `strategy-card glass ${strat.status === 'active' ? 'clickable' : 'disabled'}`;
            if (strat.status === 'active') card.onclick = () => showTrades(strat.id);
            
            card.innerHTML = `
                <div class="strat-header">
                    <h4>${strat.name}</h4>
                    <span class="perf ${strat.performance.startsWith('+') ? 'positive' : 'negative'}">${strat.performance}</span>
                </div>
                <p>${strat.desc}</p>
                <div class="strat-footer">
                    <span class="tag ${strat.status}">${strat.status.toUpperCase()}</span>
                    ${strat.status === 'active' ? '<span class="action">Trades ansehen →</span>' : ''}
                </div>
            `;
            stratList.appendChild(card);
        });

        // Render Current Chart
        renderChart(currentCoin);

    } catch (e) {
        console.error("Dashboard update failed", e);
    }
}

function switchCoin(coin) {
    currentCoin = coin;
    document.querySelectorAll('.price-tile').forEach(t => t.classList.remove('active'));
    // Find tile with the right text
    document.querySelectorAll('.price-tile').forEach(t => {
        if (t.innerText.includes(coin)) t.classList.add('active');
    });
    
    document.getElementById('chart-title').innerText = `${coin}/1H`;
    renderChart(coin);
}

let priceChart;
function renderChart(coin) {
    if (!cachedData || !cachedData.charts[coin]) return;
    
    const chartData = cachedData.charts[coin];
    const ctx = document.getElementById('priceChart').getContext('2d');
    
    if (priceChart) priceChart.destroy();

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.labels,
            datasets: [{
                label: `${coin} Price`,
                data: chartData.values,
                borderColor: '#00f2ff',
                borderWidth: 2,
                backgroundColor: 'rgba(0, 242, 255, 0.05)',
                fill: true,
                tension: 0.4,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#707a8a', font: { size: 10 } } },
                y: { grid: { color: 'rgba(255, 255, 255, 0.03)' }, ticks: { color: '#707a8a', font: { size: 10 } } }
            }
        }
    });
}

function showTrades(stratId) {
    if (!cachedData) return;
    const strat = cachedData.strategies.find(s => s.id === stratId);
    if (!strat) return;

    document.getElementById('modal-strat-name').innerText = strat.name;
    const list = document.getElementById('trade-list');
    list.innerHTML = '';

    strat.trades.forEach(t => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${t.date}</td>
            <td><b>${t.coin}</b></td>
            <td><span class="tag">${t.type}</span></td>
            <td class="${t.profit.startsWith('+') ? 'positive' : 'negative'}">${t.profit}</td>
        `;
        list.appendChild(row);
    });

    document.getElementById('trade-modal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('trade-modal').classList.add('hidden');
}

// Close modal when clicking outside
document.getElementById('trade-modal').addEventListener('click', function(e) {
    if (e.target === this) closeModal();
});

// Initial load
updateDashboard();
setInterval(updateDashboard, 60000);