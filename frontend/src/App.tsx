import React, { useState, useEffect } from 'react';
import { 
  ShoppingBag, 
  MessageSquare, 
  Package, 
  TrendingUp, 
  AlertCircle, 
  ShieldCheck, 
  User, 
  CheckCircle,
  RefreshCw,
  Send,
  Pause,
  Play,
  Search,
  ExternalLink,
  Copy,
  Plus,
  Check,
  X,
  Trash2
} from 'lucide-react';
import { Product, Order, Conversation } from './types';

const API_BASE_URL = 'https://meesho-automation-nzxa.onrender.com/api/v1';

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'products' | 'orders' | 'chats' | 'requests'>('dashboard');
  
  // V2.0 Global Command Bar Search State
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedField, setCopiedField] = useState<string | null>(null);

  // Add Product Modal State
  const [showAddProductModal, setShowAddProductModal] = useState(false);
  const [newProduct, setNewProduct] = useState({
    sku: '',
    product_name: '',
    description: '',
    actual_price: 299,
    selling_price: 499,
    meesho_url: '',
    colors: 'Red, Blue, Black',
    sizes: 'M, L, XL',
    category: 'Ethnic Wear',
    stock_quantity: 50
  });

  // Real Backend Data States
  const [loading, setLoading] = useState(false);
  const [nightlyReport, setNightlyReport] = useState<any>({
    total_orders: 0,
    total_revenue: 0,
    expected_gross_margin: 0,
    total_conversations: 0,
    human_review_queue_count: 0,
    top_requested_variants: []
  });

  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConvId, setSelectedConvId] = useState<string | null>(null);
  const [manualReplyText, setManualReplyText] = useState<string>('');

  // Keyboard shortcut listener for Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(prev => !prev);
      }
      if (e.key === 'Escape') {
        setSearchOpen(false);
        setShowAddProductModal(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Fetch Live Data from Backend
  const fetchLiveData = async () => {
    setLoading(true);
    try {
      // 1. Fetch Products
      const prodRes = await fetch(`${API_BASE_URL}/products/`);
      if (prodRes.ok) {
        const prodData = await prodRes.json();
        setProducts(prodData);
      }

      // 2. Fetch Orders
      const orderRes = await fetch(`${API_BASE_URL}/orders/`);
      if (orderRes.ok) {
        const orderData = await orderRes.json();
        setOrders(orderData);
      }

      // 3. Fetch Nightly Analytics
      const analyticsRes = await fetch(`${API_BASE_URL}/analytics/nightly-summary`);
      if (analyticsRes.ok) {
        const analyticsData = await analyticsRes.json();
        setNightlyReport(analyticsData);
      }

      // 4. Fetch Conversations
      const convRes = await fetch(`${API_BASE_URL}/conversations/`);
      if (convRes.ok) {
        const convData = await convRes.json();
        setConversations(convData);
        if (convData.length > 0 && !selectedConvId) {
          setSelectedConvId(convData[0].conversation_id);
        }
      }
    } catch (err) {
      console.warn('Backend loading status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLiveData();
  }, []);

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(label);
    setTimeout(() => setCopiedField(null), 2000);
  };

  // Submit New Product to Live Database
  const handleAddProductSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const colorVariants = newProduct.colors.split(',').map(c => ({
        type: 'color',
        value: c.trim(),
        available: true
      }));

      const sizeVariants = newProduct.sizes.split(',').map(s => ({
        type: 'size',
        value: s.trim(),
        available: true
      }));

      const payload = {
        sku: newProduct.sku || `SKU-${Date.now().toString().slice(-6)}`,
        product_name: newProduct.product_name,
        description: newProduct.description,
        actual_price: Number(newProduct.actual_price),
        selling_price: Number(newProduct.selling_price),
        currency: 'INR',
        meesho_url: newProduct.meesho_url || 'https://meesho.com',
        category: newProduct.category,
        stock_quantity: Number(newProduct.stock_quantity),
        images: ['https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=500'],
        variants: [...colorVariants, ...sizeVariants],
        faqs: [
          { question: 'Is Cash on Delivery available?', answer: 'Yes, COD is available across India.' }
        ]
      };

      // Get bearer token or post directly
      const token = localStorage.getItem('token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch(`${API_BASE_URL}/products/`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        alert('🎉 Product added successfully!');
        setShowAddProductModal(false);
        fetchLiveData();
      } else {
        const errData = await res.json();
        alert(`Error adding product: ${errData.detail || 'Check login'}`);
      }
    } catch (err) {
      alert(`Failed to connect to backend: ${err}`);
    }
  };

  const selectedConv = conversations.find(c => c.conversation_id === selectedConvId);

  const handleToggleHumanMode = async (convId: string) => {
    setConversations(prev => prev.map(c => {
      if (c.conversation_id === convId) {
        return { ...c, human_mode_active: !c.human_mode_active, requires_human_review: false };
      }
      return c;
    }));
  };

  const handleSendManualReply = (convId: string) => {
    if (!manualReplyText.trim()) return;
    setConversations(prev => prev.map(c => {
      if (c.conversation_id === convId) {
        const newMsg = {
          message_id: `m_${Date.now()}`,
          sender_type: 'HUMAN' as const,
          message_text: manualReplyText,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          ai_generated: false
        };
        return {
          ...c,
          human_mode_active: true,
          messages: [...c.messages, newMsg]
        };
      }
      return c;
    }));
    setManualReplyText('');
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col font-sans">
      {/* Top Command Center Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex justify-between items-center sticky top-0 z-40">
        <div className="flex items-center space-x-3">
          <div className="bg-pink-600 p-2 rounded-lg text-white">
            <ShoppingBag className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide">Meesho Reseller Command Center</h1>
            <p className="text-xs text-gray-400">Secure Instagram AI Sales Assistant V2.0</p>
          </div>
        </div>

        {/* Global Search Bar Activation Trigger */}
        <div className="flex-1 max-w-md mx-8">
          <button
            onClick={() => setSearchOpen(true)}
            className="w-full bg-gray-950 border border-gray-800 hover:border-gray-700 text-gray-400 px-4 py-2 rounded-xl flex justify-between items-center text-sm transition"
          >
            <div className="flex items-center space-x-2">
              <Search className="w-4 h-4 text-gray-500" />
              <span>Search products, orders, customers...</span>
            </div>
            <kbd className="bg-gray-900 border border-gray-800 px-2 py-0.5 text-[10px] text-gray-400 rounded">Ctrl K</kbd>
          </button>
        </div>
        
        <div className="flex items-center space-x-4">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-emerald-950 text-emerald-400 border border-emerald-800">
            <ShieldCheck className="w-3.5 h-3.5 mr-1" />
            Meta API Connected
          </span>
          <div className="flex items-center space-x-2 text-sm text-gray-300 bg-gray-800 px-3 py-1.5 rounded-lg border border-gray-700">
            <User className="w-4 h-4 text-pink-400" />
            <span>Store Owner</span>
          </div>
        </div>
      </header>

      {/* Global Command Bar Overlay Modal (Ctrl+K) */}
      {searchOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-start justify-center pt-20">
          <div className="bg-gray-900 border border-gray-800 w-full max-w-xl rounded-2xl shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-gray-800 flex items-center space-x-3">
              <Search className="w-5 h-5 text-pink-500" />
              <input
                type="text"
                autoFocus
                placeholder="Search orders, products, requests..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full bg-transparent text-white placeholder-gray-500 focus:outline-none text-base"
              />
            </div>
            <div className="p-4 text-xs text-gray-400 flex justify-between">
              <span>Type to search across live database facts</span>
              <span>Press ESC to close</span>
            </div>
          </div>
        </div>
      )}

      {/* Add Product Modal */}
      {showAddProductModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl">
            <div className="p-5 border-b border-gray-800 flex justify-between items-center">
              <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                <Plus className="w-5 h-5 text-pink-500" />
                <span>Add New Product to Database</span>
              </h3>
              <button
                onClick={() => setShowAddProductModal(false)}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddProductSubmit} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">Product Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Embroidered Anarkali Kurti"
                    value={newProduct.product_name}
                    onChange={e => setNewProduct({...newProduct, product_name: e.target.value})}
                    className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">SKU Code *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. KURTI-ANK-001"
                    value={newProduct.sku}
                    onChange={e => setNewProduct({...newProduct, sku: e.target.value})}
                    className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Description</label>
                <textarea
                  rows={2}
                  placeholder="Premium Rayon Embroidered Kurti Set with Dupatta"
                  value={newProduct.description}
                  onChange={e => setNewProduct({...newProduct, description: e.target.value})}
                  className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">Selling Price (₹) *</label>
                  <input
                    type="number"
                    required
                    value={newProduct.selling_price}
                    onChange={e => setNewProduct({...newProduct, selling_price: Number(e.target.value)})}
                    className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">Meesho Cost Price (₹) *</label>
                  <input
                    type="number"
                    required
                    value={newProduct.actual_price}
                    onChange={e => setNewProduct({...newProduct, actual_price: Number(e.target.value)})}
                    className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">Available Colors (Comma separated)</label>
                  <input
                    type="text"
                    value={newProduct.colors}
                    onChange={e => setNewProduct({...newProduct, colors: e.target.value})}
                    placeholder="Red, Blue, Navy Blue, Bottle Green"
                    className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">Available Sizes (Comma separated)</label>
                  <input
                    type="text"
                    value={newProduct.sizes}
                    onChange={e => setNewProduct({...newProduct, sizes: e.target.value})}
                    placeholder="S, M, L, XL, XXL"
                    className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Meesho Product Link</label>
                <input
                  type="url"
                  placeholder="https://meesho.com/s/p/..."
                  value={newProduct.meesho_url}
                  onChange={e => setNewProduct({...newProduct, meesho_url: e.target.value})}
                  className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-pink-500"
                />
              </div>

              <div className="pt-4 flex justify-end space-x-3 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => setShowAddProductModal(false)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-pink-600 hover:bg-pink-500 text-white text-sm font-semibold rounded-lg shadow-lg"
                >
                  Save Product to Database
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <nav className="bg-gray-900/60 border-b border-gray-800 px-6 flex space-x-2">
        {[
          { id: 'dashboard', label: "Tonight's Summary", icon: TrendingUp },
          { id: 'chats', label: "Live Chats & Handoff", icon: MessageSquare, badge: conversations.filter(c => c.requires_human_review).length },
          { id: 'orders', label: "Order Fulfillment Center", icon: ShoppingBag, badge: orders.length },
          { id: 'products', label: "Products Admin Window", icon: Package, badge: products.length },
          { id: 'requests', label: "Variant Requests Analytics", icon: AlertCircle, badge: nightlyReport.top_requested_variants.length },
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-2 px-4 py-3 border-b-2 font-medium text-sm transition-colors ${
                isActive
                  ? 'border-pink-500 text-pink-400 bg-pink-500/10'
                  : 'border-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/40'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
              {tab.badge ? (
                <span className="ml-1.5 px-2 py-0.5 text-xs rounded-full bg-pink-600 text-white font-semibold">
                  {tab.badge}
                </span>
              ) : null}
            </button>
          );
        })}
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto">
        {/* TAB 1: TONIGHT'S SUMMARY */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold text-white">Tonight's Business Summary</h2>
                <p className="text-sm text-gray-400">Strictly computed from PostgreSQL database facts</p>
              </div>
              <button
                onClick={fetchLiveData}
                className="flex items-center space-x-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 text-sm font-medium rounded-lg border border-gray-700 transition"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                <span>Refresh Live Data</span>
              </button>
            </div>

            {/* Metric KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="bg-gray-900 border border-gray-800 p-5 rounded-xl">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Completed Orders</p>
                <p className="text-3xl font-extrabold text-white mt-2">{nightlyReport.total_orders}</p>
                <p className="text-xs text-emerald-400 mt-1">₹{nightlyReport.total_revenue.toLocaleString()} expected revenue</p>
              </div>

              <div className="bg-gray-900 border border-gray-800 p-5 rounded-xl">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Expected Gross Margin</p>
                <p className="text-3xl font-extrabold text-emerald-400 mt-2">₹{nightlyReport.expected_gross_margin.toLocaleString()}</p>
                <p className="text-xs text-gray-400 mt-1">Based on immutable cost snapshots</p>
              </div>

              <div className="bg-gray-900 border border-gray-800 p-5 rounded-xl">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Customer Conversations</p>
                <p className="text-3xl font-extrabold text-white mt-2">{nightlyReport.total_conversations}</p>
                <p className="text-xs text-pink-400 mt-1">Automated via Groq AI</p>
              </div>

              <div className="bg-gray-900 border border-gray-800 p-5 rounded-xl">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Human Review Queue</p>
                <p className="text-3xl font-extrabold text-amber-400 mt-2">{nightlyReport.human_review_queue_count}</p>
                <p className="text-xs text-amber-400/80 mt-1">Requires owner decision</p>
              </div>
            </div>

            {/* Formatted Report Card */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Formatted Executive Report</h3>
              <div className="bg-gray-950 p-4 rounded-lg border border-gray-800 font-mono text-sm text-emerald-400 space-y-1">
                <p>--- TONIGHT'S BUSINESS REPORT ---</p>
                <p>• Orders Completed: {nightlyReport.total_orders}</p>
                <p>• Expected Revenue: ₹{nightlyReport.total_revenue}</p>
                <p>• Expected Gross Margin: ₹{nightlyReport.expected_gross_margin}</p>
                <p>• Customer Chats: {nightlyReport.total_conversations}</p>
                <p>• Needs Owner Attention: {nightlyReport.human_review_queue_count}</p>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: LIVE CHATS & HANDOFF */}
        {activeTab === 'chats' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[720px]">
            {/* Conversation List */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl flex flex-col overflow-hidden">
              <div className="p-4 border-b border-gray-800 flex justify-between items-center">
                <h3 className="font-semibold text-white">Conversations</h3>
                <span className="text-xs text-gray-400">{conversations.length} Active</span>
              </div>
              <div className="flex-1 overflow-y-auto divide-y divide-gray-800/50">
                {conversations.length === 0 ? (
                  <div className="p-8 text-center text-gray-500 text-sm">
                    No active conversations yet. When customers comment on Instagram, DMs will appear here live!
                  </div>
                ) : (
                  conversations.map(conv => {
                    const isSelected = conv.conversation_id === selectedConvId;
                    return (
                      <div
                        key={conv.conversation_id}
                        onClick={() => setSelectedConvId(conv.conversation_id)}
                        className={`p-4 cursor-pointer transition ${
                          isSelected ? 'bg-pink-500/10 border-l-4 border-pink-500' : 'hover:bg-gray-800/40'
                        }`}
                      >
                        <div className="flex justify-between items-start mb-1">
                          <span className="font-medium text-white text-sm">Customer #{conv.customer_id.slice(-6)}</span>
                          <span className="text-xs text-gray-500">{conv.last_activity_at}</span>
                        </div>
                        
                        {conv.requires_human_review && (
                          <div className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-amber-950 text-amber-400 border border-amber-800 mt-1 mb-2">
                            <AlertCircle className="w-3 h-3 mr-1" />
                            Needs Attention
                          </div>
                        )}

                        {conv.human_mode_active && (
                          <div className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-indigo-950 text-indigo-400 border border-indigo-800 mt-1 mb-2">
                            <User className="w-3 h-3 mr-1" />
                            HUMAN MODE ACTIVE
                          </div>
                        )}

                        <p className="text-xs text-gray-400 line-clamp-1">
                          {conv.messages[conv.messages.length - 1]?.message_text || 'Active session'}
                        </p>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Selected Chat Box */}
            <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-xl flex flex-col overflow-hidden">
              {selectedConv ? (
                <>
                  {/* Chat Header & Human Handoff Controls */}
                  <div className="p-4 border-b border-gray-800 flex justify-between items-center bg-gray-900/80">
                    <div>
                      <h4 className="font-semibold text-white">Customer #{selectedConv.customer_id.slice(-6)}</h4>
                      <p className="text-xs text-gray-400">Language: {selectedConv.language}</p>
                    </div>
                    
                    <div className="flex items-center space-x-3">
                      {selectedConv.human_mode_active ? (
                        <button
                          onClick={() => handleToggleHumanMode(selectedConv.conversation_id)}
                          className="flex items-center space-x-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg transition"
                        >
                          <Play className="w-3.5 h-3.5" />
                          <span>RESUME AI</span>
                        </button>
                      ) : (
                        <button
                          onClick={() => handleToggleHumanMode(selectedConv.conversation_id)}
                          className="flex items-center space-x-1.5 px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold rounded-lg transition"
                        >
                          <Pause className="w-3.5 h-3.5" />
                          <span>PAUSE AI & TAKEOVER</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Messages Area */}
                  <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-gray-950/50">
                    {selectedConv.messages.map(msg => {
                      const isCustomer = msg.sender_type === 'CUSTOMER';
                      const isAI = msg.sender_type === 'AI';
                      return (
                        <div
                          key={msg.message_id}
                          className={`flex flex-col ${isCustomer ? 'items-start' : 'items-end'}`}
                        >
                          <div className="flex items-center space-x-1 mb-1 px-1">
                            <span className="text-[10px] text-gray-400 uppercase font-semibold">
                              {msg.sender_type} {msg.ai_generated ? '(Groq AI)' : ''}
                            </span>
                            <span className="text-[10px] text-gray-500">• {msg.timestamp}</span>
                          </div>
                          <div
                            className={`max-w-md px-4 py-2.5 rounded-2xl text-sm ${
                              isCustomer
                                ? 'bg-gray-800 text-gray-100 rounded-tl-none border border-gray-700'
                                : isAI
                                ? 'bg-pink-600 text-white rounded-tr-none'
                                : 'bg-indigo-600 text-white rounded-tr-none'
                            }`}
                          >
                            {msg.message_text}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Manual Reply Bar */}
                  <div className="p-3 border-t border-gray-800 bg-gray-900 flex items-center space-x-2">
                    <input
                      type="text"
                      placeholder={
                        selectedConv.human_mode_active
                          ? 'Type your message as owner...'
                          : 'Type a message (Sending will automatically activate Human Mode)...'
                      }
                      value={manualReplyText}
                      onChange={e => setManualReplyText(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && handleSendManualReply(selectedConv.conversation_id)}
                      className="flex-1 bg-gray-950 border border-gray-700 rounded-lg px-4 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-pink-500"
                    />
                    <button
                      onClick={() => handleSendManualReply(selectedConv.conversation_id)}
                      className="px-4 py-2 bg-pink-600 hover:bg-pink-500 text-white text-sm font-medium rounded-lg flex items-center space-x-1.5 transition"
                    >
                      <Send className="w-4 h-4" />
                      <span>Send</span>
                    </button>
                  </div>
                </>
              ) : (
                <div className="flex-1 flex items-center justify-center text-gray-500">
                  Select a conversation to inspect
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: ORDER FULFILLMENT CENTER */}
        {activeTab === 'orders' && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white">Order Fulfillment Center</h2>
            <p className="text-sm text-gray-400">Complete fulfillment details - Everything needed for fast manual Meesho ordering</p>

            {orders.length === 0 ? (
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center text-gray-400 space-y-3">
                <ShoppingBag className="w-12 h-12 text-gray-600 mx-auto" />
                <h3 className="text-lg font-bold text-white">No Orders Placed Yet</h3>
                <p className="text-xs max-w-md mx-auto text-gray-500">
                  When customers place orders via Instagram DMs, their confirmed delivery addresses, phone numbers, and Meesho product links will appear here automatically for single-click copying!
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {orders.map(o => (
                  <div key={o.order_id} className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-6">
                    {/* Fulfillment Card Header */}
                    <div className="flex justify-between items-start border-b border-gray-800 pb-4">
                      <div>
                        <div className="flex items-center space-x-3">
                          <span className="text-xl font-extrabold text-pink-400 font-mono">{o.order_id}</span>
                          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
                            <CheckCircle className="w-3.5 h-3.5 mr-1" />
                            {o.order_state}
                          </span>
                        </div>
                        <p className="text-xs text-gray-400 mt-1">Confirmed on {o.created_at}</p>
                      </div>

                      {/* Fast External Action Buttons */}
                      <div className="flex items-center space-x-3">
                        <a
                          href="https://meesho.com"
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center space-x-1.5 px-3 py-1.5 bg-pink-600 hover:bg-pink-500 text-white text-xs font-semibold rounded-lg transition"
                        >
                          <span>OPEN MEESHO</span>
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </div>
                    </div>

                    {/* Fulfillment Card Body Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      {/* Item & Financials */}
                      <div className="bg-gray-950 p-4 rounded-xl border border-gray-850 space-y-3">
                        <h4 className="text-xs font-semibold uppercase text-gray-400 tracking-wider">Product & Financials</h4>
                        {o.items.map(item => (
                          <div key={item.item_id} className="space-y-2">
                            <p className="text-base font-bold text-white">{item.product_name}</p>
                            <p className="text-xs text-gray-400">Variant: <span className="text-gray-200 font-medium">{item.variant}</span></p>
                            <p className="text-xs text-gray-400">Quantity: <span className="text-gray-200 font-medium">{item.quantity}</span></p>
                            <div className="pt-2 border-t border-gray-800 space-y-1 text-xs">
                              <div className="flex justify-between"><span className="text-gray-400">Source Price:</span> <span>₹{item.actual_price}</span></div>
                              <div className="flex justify-between"><span className="text-gray-400">Selling Price:</span> <span className="font-semibold text-white">₹{item.selling_price}</span></div>
                              <div className="flex justify-between text-emerald-400 font-bold"><span className="text-gray-400">Expected Margin:</span> <span>+₹{o.expected_margin}</span></div>
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Delivery Address & Customer Details */}
                      <div className="bg-gray-950 p-4 rounded-xl border border-gray-850 space-y-3">
                        <h4 className="text-xs font-semibold uppercase text-gray-400 tracking-wider">Delivery Information</h4>
                        <div className="space-y-1.5 text-sm">
                          <p className="font-bold text-white">{o.customer_name}</p>
                          <p className="text-xs text-gray-300 font-mono">{o.phone}</p>
                          <p className="text-xs text-gray-400">{o.house_building}, {o.road_area_colony}</p>
                        </div>
                      </div>

                      {/* One-Click Copy Helpers */}
                      <div className="bg-gray-950 p-4 rounded-xl border border-gray-850 flex flex-col justify-between">
                        <h4 className="text-xs font-semibold uppercase text-gray-400 tracking-wider">One-Click Copy Helpers</h4>
                        <div className="space-y-2 my-auto">
                          <button
                            onClick={() => copyToClipboard(o.customer_name, 'name')}
                            className="w-full flex items-center justify-between px-3 py-1.5 bg-gray-900 hover:bg-gray-850 border border-gray-800 rounded-lg text-xs text-gray-200 transition"
                          >
                            <span>Copy Customer Name</span>
                            {copiedField === 'name' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-gray-400" />}
                          </button>
                          <button
                            onClick={() => copyToClipboard(o.phone, 'phone')}
                            className="w-full flex items-center justify-between px-3 py-1.5 bg-gray-900 hover:bg-gray-850 border border-gray-800 rounded-lg text-xs text-gray-200 transition"
                          >
                            <span>Copy Phone Number</span>
                            {copiedField === 'phone' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-gray-400" />}
                          </button>
                          <button
                            onClick={() => copyToClipboard(`${o.house_building}, ${o.road_area_colony}`, 'address')}
                            className="w-full flex items-center justify-between px-3 py-1.5 bg-gray-900 hover:bg-gray-850 border border-gray-800 rounded-lg text-xs text-gray-200 transition"
                          >
                            <span>Copy Full Address</span>
                            {copiedField === 'address' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-gray-400" />}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 4: PRODUCTS & PRICING ADMIN WINDOW */}
        {activeTab === 'products' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold text-white">Product Management Window</h2>
                <p className="text-sm text-gray-400">Manage your product catalog, prices, and available colors/sizes</p>
              </div>
              <button
                onClick={() => setShowAddProductModal(true)}
                className="px-4 py-2 bg-pink-600 hover:bg-pink-500 text-white text-sm font-semibold rounded-lg flex items-center space-x-1.5 transition shadow-lg"
              >
                <Plus className="w-4 h-4" />
                <span>+ Add Product</span>
              </button>
            </div>

            {products.length === 0 ? (
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center text-gray-400 space-y-4">
                <Package className="w-12 h-12 text-gray-600 mx-auto" />
                <h3 className="text-lg font-bold text-white">No Products in Database Yet</h3>
                <p className="text-xs max-w-md mx-auto text-gray-500">
                  Click the "+ Add Product" button above to add your first product with price, colors, sizes, and Meesho link!
                </p>
                <button
                  onClick={() => setShowAddProductModal(true)}
                  className="px-5 py-2.5 bg-pink-600 hover:bg-pink-500 text-white text-sm font-bold rounded-xl"
                >
                  + Add Your First Product
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {products.map(p => (
                  <div key={p.product_id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-xs font-mono text-pink-400">{p.sku}</span>
                        <h3 className="text-lg font-bold text-white">{p.product_name}</h3>
                      </div>
                      <span className="px-2 py-0.5 rounded text-xs bg-emerald-950 text-emerald-400 border border-emerald-800 font-medium">
                        Active
                      </span>
                    </div>

                    <p className="text-sm text-gray-400">{p.description}</p>

                    <div className="grid grid-cols-2 gap-4 bg-gray-950 p-3 rounded-lg border border-gray-850">
                      <div>
                        <span className="text-xs text-gray-500">Meesho Cost Price</span>
                        <p className="text-base font-semibold text-gray-300">₹{p.actual_price}</p>
                      </div>
                      <div>
                        <span className="text-xs text-gray-500">Selling Price</span>
                        <p className="text-base font-bold text-pink-400">₹{p.selling_price}</p>
                      </div>
                    </div>

                    <div>
                      <span className="text-xs font-semibold text-gray-400 block mb-2">Variants Availability:</span>
                      <div className="flex flex-wrap gap-2">
                        {p.variants.map(v => (
                          <span
                            key={v.variant_id || v.value}
                            className={`px-2.5 py-1 rounded text-xs font-medium border ${
                              v.available
                                ? 'bg-gray-800 text-gray-200 border-gray-700'
                                : 'bg-red-950 text-red-400 border-red-900 line-through'
                            }`}
                          >
                            {v.value} {v.available ? '✓' : '(Out of stock)'}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 5: VARIANT REQUESTS */}
        {activeTab === 'requests' && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white">Customer Variant Requests</h2>
            <p className="text-sm text-gray-400">Automated market demand detection for unstocked colors, sizes, or variants</p>

            {nightlyReport.top_requested_variants.length === 0 ? (
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center text-gray-400 space-y-2">
                <AlertCircle className="w-10 h-10 text-gray-600 mx-auto" />
                <h3 className="text-base font-bold text-white">No Out-of-Stock Requests Logged Yet</h3>
                <p className="text-xs text-gray-500">When customers ask for unstocked colors or sizes in DMs, AI will log demand trends here!</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {nightlyReport.top_requested_variants.map((req: any, i: number) => (
                  <div key={i} className="bg-gray-900 border border-gray-800 p-5 rounded-xl flex justify-between items-center">
                    <div>
                      <span className="text-xs text-gray-500 uppercase font-semibold">Requested Item</span>
                      <p className="text-lg font-bold text-white mt-1">{req.value}</p>
                    </div>
                    <div className="bg-pink-950 text-pink-400 border border-pink-800 px-3 py-1.5 rounded-lg text-sm font-extrabold">
                      {req.count} Requests
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
