import { useEffect, useState } from 'react'
import { createClient } from '@supabase/supabase-js'
import { ArrowUpCircle, ArrowDownCircle, Activity, TrendingUp, DollarSign } from 'lucide-react'

// Supabase Config (Public Anon Key)
const supabaseUrl = 'https://yrkdbwgtwbncficegjjb.supabase.co'
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inlya2Rid2d0d2JuY2ZpY2VnampiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA5MDY5NjAsImV4cCI6MjA4NjQ4Mjk2MH0.hZ70RNiHzscN0VKl2T29XVy4Rq6Vhe8PoDDV7jcxtdw'
const supabase = createClient(supabaseUrl, supabaseKey)

function App() {
  const [signals, setSignals] = useState([])
  const [stats, setStats] = useState({ total: 0, wins: 0, active: 0, winRate: 0 })

  useEffect(() => {
    fetchSignals()
    
    // Realtime subscription
    const channel = supabase
      .channel('table-db-changes')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'signals' }, (payload) => {
        fetchSignals()
      })
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [])

  async function fetchSignals() {
    const { data, error } = await supabase
      .table('signals')
      .select('*')
      .order('timestamp', { ascending: false })
    
    if (error) console.error('Error:', error)
    else {
      setSignals(data)
      calculateStats(data)
    }
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

  return (
    <div className="min-h-screen bg-gray-950 p-4 md:p-8 font-sans">
      <div className="max-w-6xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            KryptoWahnsinn17 Dashboard
          </h1>
          <p className="text-gray-400">Live Trading Signals by Hansi AI</p>
        </header>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card title="Active Trades" value={stats.active} icon={<Activity className="text-blue-400" />} />
          <Card title="Closed Trades" value={stats.total} icon={<TrendingUp className="text-purple-400" />} />
          <Card title="Win Rate" value={`${stats.winRate.toFixed(1)}%`} icon={<ArrowUpCircle className="text-green-400" />} />
          <Card title="Total Signals" value={signals.length} icon={<DollarSign className="text-yellow-400" />} />
        </div>

        {/* Signals Table */}
        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden shadow-2xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-gray-800 text-gray-400 uppercase text-xs">
                <tr>
                  <th className="p-4">Zeit</th>
                  <th className="p-4">Symbol</th>
                  <th className="p-4">Signal</th>
                  <th className="p-4">Strategie</th>
                  <th className="p-4">Entry</th>
                  <th className="p-4">PnL</th>
                  <th className="p-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {signals.map((s) => (
                  <tr key={s.id} className="hover:bg-gray-800/50 transition-colors">
                    <td className="p-4 text-gray-400 text-sm">{formatDate(s.timestamp)}</td>
                    <td className="p-4 font-bold">{s.symbol} <span className="text-xs text-gray-500 font-normal">({s.interval})</span></td>
                    <td className="p-4">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-bold ${
                        s.signal === 'BUY' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                      }`}>
                        {s.signal === 'BUY' ? <ArrowUpCircle size={14} /> : <ArrowDownCircle size={14} />}
                        {s.signal}
                      </span>
                    </td>
                    <td className="p-4 text-gray-300 text-sm">{s.strategy}</td>
                    <td className="p-4 text-gray-300">${Number(s.entry_price).toFixed(2)}</td>
                    <td className={`p-4 font-mono font-bold ${
                      !s.profit_loss ? 'text-gray-500' : s.profit_loss > 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {s.profit_loss ? `${s.profit_loss > 0 ? '+' : ''}${Number(s.profit_loss).toFixed(2)}%` : '-'}
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded text-xs ${
                        s.status === 'ACTIVE' ? 'bg-blue-500/20 text-blue-400 animate-pulse' : 'bg-gray-700 text-gray-300'
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
      </div>
    </div>
  )
}

function Card({ title, value, icon }) {
  return (
    <div className="bg-gray-900 p-6 rounded-xl border border-gray-800 flex items-center justify-between">
      <div>
        <p className="text-gray-400 text-sm uppercase">{title}</p>
        <p className="text-2xl font-bold mt-1">{value}</p>
      </div>
      <div className="p-3 bg-gray-800 rounded-lg">{icon}</div>
    </div>
  )
}

export default App
