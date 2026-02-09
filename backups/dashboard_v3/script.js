let cachedData = null;
let currentCoin = 'BTC';

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

        // Update Signal Banner
        const banner = document.getElementById('signal-banner');
        const bannerText = document.getElementById('signal-text');
        const activeSignals = data.signals.filter(s => s.type !== 'STATUS');
        
        if (activeSignals.length > 0) {
            banner.classList.remove('hidden');
            const s = activeSignals[0];
            bannerText.innerText = `SIGNAL: ${s.symbol} ${s.signal} @ ${s.price} (${s.timeframe})`;
        } else {
            banner.classList.add('hidden');
        }

        // Render Current Chart
        renderChart(currentCoin);
        
        if (window.lucide) lucide.createIcons();

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

// Initial load
updateDashboard();
setInterval(updateDashboard, 60000);