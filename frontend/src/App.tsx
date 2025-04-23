import { useState, useEffect } from 'react'
import MarketSelector from './components/MarketSelector'
import TruePriceChart from './components/TruePriceChart'
import Leaderboard from './components/Leaderboard'
import AlertForm from './components/AlertForm'
import MarketRationality from './components/MarketRationality'
import { Market } from './types'

function App() {
  const [selectedMarket, setSelectedMarket] = useState<Market | null>(null)
  const [markets, setMarkets] = useState<Market[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Fetch markets on mount
    fetch('/api/markets')
      .then(response => response.json())
      .then(data => {
        setMarkets(data)
        if (data.length > 0) {
          setSelectedMarket(data[0])
        }
        setLoading(false)
      })
      .catch(error => {
        console.error('Error fetching markets:', error)
        setLoading(false)
      })
  }, [])

  const handleMarketChange = (market: Market) => {
    setSelectedMarket(market)
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">Polymarket Monitor</h1>
        </div>
      </header>
      
      <main>
        <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          {loading ? (
            <div className="text-center py-10">
              <p className="text-gray-500">Loading market data...</p>
            </div>
          ) : (
            <>
              <div className="mb-6">
                <MarketSelector 
                  markets={markets} 
                  selectedMarket={selectedMarket} 
                  onMarketChange={handleMarketChange}
                />
              </div>
              
              {selectedMarket && (
                <>
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2">
                      <div className="bg-white shadow rounded-lg p-4">
                        <h2 className="text-xl font-semibold mb-4">True Price vs. Mid Price</h2>
                        <TruePriceChart marketId={selectedMarket.id} />
                      </div>
                    </div>
                    
                    <div className="lg:col-span-1">
                      <div className="bg-white shadow rounded-lg p-4 mb-6">
                        <h2 className="text-xl font-semibold mb-4">Leaderboard</h2>
                        <Leaderboard marketId={selectedMarket.id} />
                      </div>
                      
                      <div className="bg-white shadow rounded-lg p-4">
                        <h2 className="text-xl font-semibold mb-4">Price Alerts</h2>
                        <AlertForm marketId={selectedMarket.id} />
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-6">
                    <MarketRationality marketId={selectedMarket.id} />
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </main>
      
      <footer className="bg-white mt-8 py-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-gray-500 text-sm">
            Polymarket Monitor - Real-time market monitoring and analysis
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App 