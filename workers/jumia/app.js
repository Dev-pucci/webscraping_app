import React, { useState, useEffect } from 'react';
import { Search, Download, ShoppingBag, Star, TrendingUp, Filter, Loader2, ExternalLink, Zap } from 'lucide-react';

const JumiaScraperApp = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryUrl, setCategoryUrl] = useState('');
  const [maxPages, setMaxPages] = useState(3);
  const [outputFormat, setOutputFormat] = useState('json');
  const [loading, setLoading] = useState(false);
  const [products, setProducts] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [searchType, setSearchType] = useState('search'); // 'search' or 'category'
  const [error, setError] = useState('');

  // Simulate backend API call
  const scrapeProducts = async () => {
    if (!searchQuery && !categoryUrl) {
      setError('Please enter a search query or category URL');
      return;
    }

    setLoading(true);
    setError('');
    
    try {
      // Simulate API call to Python backend
      // In real implementation, this would call your Flask/FastAPI endpoint
      const response = await fetch('/api/scrape', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          search: searchType === 'search' ? searchQuery : null,
          categoryUrl: searchType === 'category' ? categoryUrl : null,
          pages: maxPages,
          format: outputFormat
        })
      });

      if (!response.ok) {
        throw new Error('Scraping failed');
      }

      const data = await response.json();
      
      // For demo purposes, generate sample data based on your CSV structure
      const sampleProducts = generateSampleProducts(searchQuery || 'phones');
      setProducts(sampleProducts);
      calculateStatistics(sampleProducts);
      
    } catch (err) {
      setError('Error connecting to backend. Make sure your Python server is running.');
      console.error('Scraping error:', err);
    } finally {
      setLoading(false);
    }
  };

  const generateSampleProducts = (query) => {
    const brands = ['SAMSUNG', 'XIAOMI', 'INFINIX', 'TECNO', 'ITEL', 'OPPO', 'REALME'];
    const products = [];
    
    for (let i = 0; i < 20; i++) {
      const brand = brands[Math.floor(Math.random() * brands.length)];
      const price = Math.floor(Math.random() * 50000) + 5000;
      const originalPrice = price + Math.floor(Math.random() * 10000);
      const discount = Math.floor(((originalPrice - price) / originalPrice) * 100);
      const rating = (Math.random() * 2 + 3).toFixed(1);
      const reviews = Math.floor(Math.random() * 500) + 10;
      
      products.push({
        name: `${brand} ${query} ${i + 1} - 6.5" Display, ${Math.floor(Math.random() * 8) + 2}GB RAM`,
        price: `KSh ${price.toLocaleString()}`,
        original_price: discount > 5 ? `KSh ${originalPrice.toLocaleString()}` : 'N/A',
        discount: discount > 5 ? `${discount}%` : 'N/A',
        rating: `${rating}/5`,
        reviews_count: `${reviews} reviews`,
        image_url: `https://ke.jumia.is/unsafe/fit-in/300x300/filters:fill(white)/product/${Math.floor(Math.random() * 999999)}.jpg`,
        product_url: `https://www.jumia.co.ke/product-${i + 1}.html`,
        brand: brand,
        category: 'Android Phones'
      });
    }
    
    return products;
  };

  const calculateStatistics = (products) => {
    const totalProducts = products.length;
    const withPrices = products.filter(p => p.price !== 'N/A').length;
    const withRatings = products.filter(p => p.rating !== 'N/A').length;
    const withDiscounts = products.filter(p => p.discount !== 'N/A').length;
    
    const brandCounts = {};
    products.forEach(p => {
      if (p.brand !== 'N/A') {
        brandCounts[p.brand] = (brandCounts[p.brand] || 0) + 1;
      }
    });

    setStatistics({
      total: totalProducts,
      priceSuccess: Math.round((withPrices / totalProducts) * 100),
      ratingSuccess: Math.round((withRatings / totalProducts) * 100),
      discountSuccess: Math.round((withDiscounts / totalProducts) * 100),
      topBrands: Object.entries(brandCounts)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 5)
    });
  };

  const downloadData = () => {
    const dataStr = outputFormat === 'json' 
      ? JSON.stringify(products, null, 2)
      : convertToCSV(products);
    
    const dataBlob = new Blob([dataStr], { type: outputFormat === 'json' ? 'application/json' : 'text/csv' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `jumia_products.${outputFormat}`;
    link.click();
  };

  const convertToCSV = (data) => {
    if (!data.length) return '';
    
    const headers = Object.keys(data[0]);
    const csvContent = [
      headers.join(','),
      ...data.map(row => 
        headers.map(header => 
          JSON.stringify(row[header] || '')
        ).join(',')
      )
    ].join('\n');
    
    return csvContent;
  };

  const ProductCard = ({ product }) => (
    <div className="bg-white rounded-lg shadow-md hover:shadow-xl transition-all duration-300 border border-gray-100 overflow-hidden">
      <div className="relative">
        <img 
          src={product.image_url} 
          alt={product.name}
          className="w-full h-48 object-cover bg-gray-100"
          onError={(e) => {
            e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgdmlld0JveD0iMCAwIDMwMCAyMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iMjAwIiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik0xMzAgODBIMTcwVjEyMEgxMzBWODBaIiBmaWxsPSIjRDFENURCIi8+CjwvnN2Zz4K';
          }}
        />
        {product.discount !== 'N/A' && (
          <div className="absolute top-2 right-2 bg-red-500 text-white px-2 py-1 rounded-full text-xs font-bold">
            -{product.discount}
          </div>
        )}
      </div>
      
      <div className="p-4">
        <h3 className="font-semibold text-gray-800 text-sm mb-2 line-clamp-2 min-h-[2.5rem]">
          {product.name}
        </h3>
        
        <div className="space-y-2 mb-3">
          <div className="flex items-center justify-between">
            <span className="text-lg font-bold text-gray-900">{product.price}</span>
            {product.original_price !== 'N/A' && (
              <span className="text-sm text-gray-500 line-through">{product.original_price}</span>
            )}
          </div>
          
          {product.rating !== 'N/A' && (
            <div className="flex items-center space-x-1">
              <Star className="w-4 h-4 text-yellow-400 fill-current" />
              <span className="text-sm text-gray-600">{product.rating}</span>
              <span className="text-xs text-gray-400">({product.reviews_count})</span>
            </div>
          )}
          
          <div className="flex items-center justify-between">
            <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">
              {product.brand}
            </span>
            <a 
              href={product.product_url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-blue-500 hover:text-blue-700 transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-orange-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-orange-500 rounded-lg">
              <ShoppingBag className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Jumia Scraper</h1>
              <p className="text-sm text-gray-600">Extract product data from Jumia Kenya</p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search Controls */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Search Type Toggle */}
            <div className="space-y-4">
              <div className="flex space-x-4">
                <button
                  onClick={() => setSearchType('search')}
                  className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
                    searchType === 'search' 
                      ? 'bg-blue-500 text-white' 
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  <Search className="w-4 h-4 inline mr-2" />
                  Search Products
                </button>
                <button
                  onClick={() => setSearchType('category')}
                  className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
                    searchType === 'category' 
                      ? 'bg-blue-500 text-white' 
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  <Filter className="w-4 h-4 inline mr-2" />
                  Category URL
                </button>
              </div>

              {searchType === 'search' ? (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Search Query
                  </label>
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="e.g., smartphone, laptop, headphones"
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Category URL
                  </label>
                  <input
                    type="url"
                    value={categoryUrl}
                    onChange={(e) => setCategoryUrl(e.target.value)}
                    placeholder="https://www.jumia.co.ke/phones/"
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              )}
            </div>

            {/* Options */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Pages to Scrape
                </label>
                <input
                  type="number"
                  value={maxPages}
                  onChange={(e) => setMaxPages(parseInt(e.target.value))}
                  min="1"
                  max="10"
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Output Format
                </label>
                <select
                  value={outputFormat}
                  onChange={(e) => setOutputFormat(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="json">JSON</option>
                  <option value="csv">CSV</option>
                </select>
              </div>
            </div>
          </div>

          {error && (
            <div className="mt-4 p-3 bg-red-100 border border-red-300 rounded-lg text-red-700">
              {error}
            </div>
          )}

          <div className="mt-6 flex space-x-4">
            <button
              onClick={scrapeProducts}
              disabled={loading}
              className="flex-1 bg-gradient-to-r from-blue-500 to-blue-600 text-white py-3 px-6 rounded-lg font-medium hover:from-blue-600 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center space-x-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Scraping...</span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  <span>Start Scraping</span>
                </>
              )}
            </button>

            {products.length > 0 && (
              <button
                onClick={downloadData}
                className="bg-green-500 text-white py-3 px-6 rounded-lg font-medium hover:bg-green-600 transition-colors flex items-center space-x-2"
              >
                <Download className="w-4 h-4" />
                <span>Download {outputFormat.toUpperCase()}</span>
              </button>
            )}
          </div>
        </div>

        {/* Statistics */}
        {statistics && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <ShoppingBag className="w-6 h-6 text-blue-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Total Products</p>
                  <p className="text-2xl font-bold text-gray-900">{statistics.total}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center">
                <div className="p-2 bg-green-100 rounded-lg">
                  <TrendingUp className="w-6 h-6 text-green-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Price Success</p>
                  <p className="text-2xl font-bold text-gray-900">{statistics.priceSuccess}%</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center">
                <div className="p-2 bg-yellow-100 rounded-lg">
                  <Star className="w-6 h-6 text-yellow-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Rating Success</p>
                  <p className="text-2xl font-bold text-gray-900">{statistics.ratingSuccess}%</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-md p-6">
              <div className="flex items-center">
                <div className="p-2 bg-red-100 rounded-lg">
                  <Filter className="w-6 h-6 text-red-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-500">Discounts Found</p>
                  <p className="text-2xl font-bold text-gray-900">{statistics.discountSuccess}%</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Top Brands */}
        {statistics && statistics.topBrands.length > 0 && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Brands Found</h3>
            <div className="flex flex-wrap gap-3">
              {statistics.topBrands.map(([brand, count]) => (
                <div key={brand} className="bg-gray-100 rounded-full px-4 py-2">
                  <span className="font-medium text-gray-800">{brand}</span>
                  <span className="text-gray-600 ml-2">({count})</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Products Grid */}
        {products.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900">
                Scraped Products ({products.length})
              </h2>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {products.map((product, index) => (
                <ProductCard key={index} product={product} />
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && products.length === 0 && (
          <div className="text-center py-12">
            <ShoppingBag className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Products Yet</h3>
            <p className="text-gray-600">Enter a search term or category URL to start scraping products</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default JumiaScraperApp;