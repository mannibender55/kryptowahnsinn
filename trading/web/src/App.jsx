import { useEffect, useState } from 'react'
import { createClient } from '@supabase/supabase-js'
import { ArrowUpCircle, ArrowDownCircle, Activity, TrendingUp, DollarSign, Filter, Zap, Bot } from 'lucide-react'

// Supabase Config
const supabaseUrl = 'https://yrkdbwgtwbncficegjjb.supabase.co'
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inlya2Rid2d0d2JuY2ZpY2VnampiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA5MDY5NjAsImV4cCI6MjA4NjQ4Mjk2MH0.hZ70RNiHzscN0VKl2T29XVy4Rq6Vhe8PoDDV7jcxtdw'
const supabase = createClient(supabaseUrl, supabaseKey)

function App() {
  const [signals, setSignals] = useState([])
  const [stats, setStats] = useState({ total: 0, wins: 0, active: 0, winRate: 0 })
  const [filter, setFilter] = useState('ALL')
  const [strategies, setStrategies] = useState([])
  const [candles, setCandles] = useState({})

  useEffect(() => {
    fetchSignals()
    fetchCandles()
    
    const channel = supabase
      .channel('table-db-changes')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'signals' }, () => fetchSignals())
      .subscribe()

    return () => supabase.removeChannel(channel)
  }, [])

  async function fetchSignals() {
    const { data, error } = await supabase
      .table('signals')
      .select('*')
      .order('timestamp', { ascending: false })
    
    if (!error && data) {
      setSignals(data)
      const uniqueStrats = [...new Set(data.map(s => s.strategy))]
      setStrategies(uniqueStrats)
      calculateStats(data)
    }
  }

  async function fetchCandles() {
    const symbols = ['BTC', 'ETH', 'SOL']
    const results = {}
    for (const sym of symbols) {
      const { data } = await supabase
        .table('candles')
        .select('*')
        .eq('symbol', sym)
        .eq('timeframe', '1h')
        .order('timestamp', { ascending: false })
        .limit(1)
      if (data && data[0]) results[sym] = data[0]
    }
    setCandles(results)
  }

  function calculateStats(data) {
    const total = data.filter(s => s.status === 'CLOSED').length
    const wins = data.filter(s => s.status === 'CLOSED' && s.profit_loss > 0).length
    const active = data.filter(s => s.status === 'ACTIVE').length
    const winRate = total > 0 ? (wins / total) * 100 : 0
    setStats({ total, wins, active, winRate })
  }

  function formatDate(isoString) {
    return new Date(isoString).toLocaleString('de-DE', {
      day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
    })
  }

  const filteredSignals = filter === 'ALL' 
    ? signals 
    : signals.filter(s => s.strategy === filter)

  return (
    <div className="min-h-screen bg-gray-950 p-4 md:p-8 font-sans">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 via-purple-500 to-pink-500 bg-clip-text text-transparent">
              KryptoWahnsinn
            </h1>
            <p className="text-gray-400 flex items-center gap-2 mt-1">
              <Bot size={16} /> 
              AI Trading Signals • Live Data
            </p>
          </div>
          <div className="flex gap-2 mt-4 md:mt-0">
            {Object.entries(candles).map(([sym, data]) => (
              <div key={sym} className="bg-gray-900 px-4 py-2 rounded-lg border border-gray-800">
                <span className="text-gray-400 text-xs">{sym}</span>
                <p className="text-lg font-bold text-white">${Number(data.close).toLocaleString()}</p>
              </div>
            ))}
          </div>
        </header>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <Card 
            title="Aktive Signale" 
            value={stats.active} 
            icon={<Activity className="text-blue-400" />} 
            color="blue"
          />
          <Card 
            title="Geschlossene" 
            value={stats.total} 
            icon={<TrendingUp className="text-purple-400" />} 
            color="purple"
          />
          <Card 
            title="Win Rate" 
            value={`${stats.winRate.toFixed(1)}%`} 
            icon={<ArrowUpCircle className="text-green-400" />} 
            color="green"
          />
          <Card 
            title="Gesamt Signale" 
            value={signals.length} 
            icon={<DollarSign className="text-yellow-400" />} 
            color="yellow"
          />
        </div>

        {/* Strategy Filter */}
        <div className="flex gap-2 mb-6 flex-wrap">
          <button
            onClick={() => setFilter('ALL')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              filter === 'ALL' 
                ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white' 
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            Alle Strategien
          </button>
          {strategies.map(strat => (
            <button
              key={strat}
              onClick={() => setFilter(strat)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                filter === strat
                  ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              <Zap size={14} /> {strat}
            </button>
          ))}
        </div>

        {/* Signals Table */}
        <div className="bg-gray-900/50 backdrop-blur rounded-2xl border border-gray-800 overflow-hidden shadow-2xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-gray-800/50 text-gray-400 uppercase text-xs">
                <tr>
                  <th className="p-4">Zeit</th>
                  <th className="p-4">Symbol</th>
                  <th className="p-4">Signal</th>
                  <th className="p-4">Strategie</th>
                  <th className="p-4">Entry</th>
                  <th className="p-4">SL</th>
                  <th className="p-4">TP</th>
                  <th className="p-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {filteredSignals.slice(0, 50).map((s) => (
                  <tr key={s.id} className="hover:bg-gray-800/30 transition-colors">
                    <td className="p-4 text-gray-400 text-sm">{formatDate(s.timestamp)}</td>
                    <td className="p-4">
                      <span className="font-bold text-white">{s.symbol}</span>
                      <span className="text-xs text-gray-500 ml-1">({s.interval})</span>
                    </td>
                    <td className="p-4">
                      <span className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-bold ${
                        s.signal === 'BUY' 
                          ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
                          : 'bg-red-500/20 text-red-400 border border-red-500/30'
                      }`}>
                        {s.signal === 'BUY' ? <ArrowUpCircle size={14} /> : <ArrowDownCircle size={14} />}
                        {s.signal}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className="px-2 py-1 bg-purple-500/20 text-purple-400 rounded text-xs">
                        {s.strategy}
                      </span>
                    </td>
                    <td className="p-4 text-white font-mono">${Number(s.entry_price).toLocaleString()}</td>
                    <td className="p-4 text-red-400 font-mono">${Number(s.sl_price).toLocaleString()}</td>
                    <td className="p-4 text-green-400 font-mono">${Number(s.tp_price).toLocaleString()}</td>
                    <td className="p-4">
                      <span className={`px-3 py-1.5 rounded-full text-xs font-medium ${
                        s.status === 'ACTIVE' 
                          ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30 animate-pulse' 
                          : 'bg-gray-700 text-gray-300'
                      }`}>
                        {s.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <footer className="mt-8 text-center text-gray-500 text-sm">
          <p>Letzte Aktualisierung: {new Date().toLocaleString('de-DE')}</p>
          <p className="mt-1">Daten von Hyperliquid • Powered by Supabase</p>
        </footer>
      </div>
    </div>
  )
}

function Card({ title, value, icon, color }) {
  const colors = {
    blue: 'from-blue-500/20 to-blue-600/10 border-blue-500/30',
    purple: 'from-purple-500/20 to-purple-600/10 border-purple-500/30', 
    green: 'from-green-500/20 to-green-600/10 border-green-500/30',
    yellow: 'from-yellow-500/20 to-yellow-600/10 border-yellow-500/30'
  }
  
  return (
    <div className={`bg-gradient-to-br ${colors[color]} p-6 rounded-2xl border border-gray-800 flex items-center justify-between`}>
      <div>
        <p className="text-gray-400 text-sm uppercase tracking-wide">{title}</p>
        <p className="text-3xl font-bold mt-1 bg-gradient-to-r from-white to-gray-300 bg-clip-text text-transparent">{value}</p>
      </div>
      <div className="p-3 bg-gray-900/50 rounded-xl">{icon}</div>
    </div>
  )
}

export default App
