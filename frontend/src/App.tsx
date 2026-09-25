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
  FileText,
  Clock
} from 'lucide-react';
import { Product, Order, Conversation, CustomerRequest } from './types';

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'products' | 'orders' | 'chats' | 'requests'>('dashboard');
  
  // V2.0 Global Command Bar Search State
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedField, setCopiedField] = useState<string | null>(null);

  // Keyboard shortcut listener for Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(prev => !prev);
      }
      if (e.key === 'Escape') {
        setSearchOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const copyToClipboard = (text: str, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(label);
    setTimeout(() => setCopiedField(null), 2000);
  };

  // Demo State & V2.0 Data Models
  const [nightlyReport, setNightlyReport] = useState<any>({
    total_orders: 11,
    total_revenue: 6240,
    expected_gross_margin: 2180,
    total_conversations: 42,
    human_review_queue_count: 3,
    top_requested_variants: [
      { value: "Blue Color", count: 7 },
      { value: "Green Color", count: 3 },
      { value: "Size XL", count: 4 }
    ]
  });

  const [products, setProducts] = useState<Product[]>([
    {
      product_id: "p1",
      sku: "PROD-BAG-001",
      product_name: "Women's Sling Bag",
      description: "Premium PU Leather Sling Bag with Gold Chain Strap",
      actual_price: 299,
      selling_price: 449,
      currency: "INR",
      meesho_url: "https://meesho.com/s/p/bag01",
      images: ["https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=400"],
      variants: [
        { variant_id: "v1", type: "color", value: "Black", available: true },
        { variant_id: "v2", type: "color", value: "Brown", available: true },
        { variant_id: "v3", type: "color", value: "Pink", available: false }
      ],
      faqs: [
        { faq_id: "f1", question: "Is COD available?", answer: "Yes, Cash on Delivery is available.", verified_by_owner: true }
      ],
      active: true
    }
  ]);

  const [orders, setOrders] = useState<Order[]>([
    {
      order_id: "ORD-1042",
      customer_name: "Rahul Sharma",
      phone: "9876543210",
      house_building: "Flat B-42, Royal Heights",
      road_area_colony: "Rohini Sector 7, New Delhi",
      total_selling_price: 1347,
      total_actual_cost: 897,
      expected_margin: 450,
      order_state: "CONFIRMED",
      created_at: "2026-09-25 02:20",
      items: [
        { item_id: "i1", product_name: "Women's Sling Bag", actual_price: 299, selling_price: 449, variant: "Color: Brown", quantity: 3 }
      ]
    }
  ]);

  const [conversations, setConversations] = useState<Conversation[]>([
    {
      conversation_id: "conv-101",
      customer_id: "cust-rahul",
      language: "hinglish",
      requires_human_review: true,
      human_review_reason: "Customer requested unavailable variant (Pink)",
      human_mode_active: false,
      last_activity_at: "2026-09-25 02:15",
      messages: [
        { message_id: "m1", sender_type: "CUSTOMER", message_text: "bhai pink wala milega kya?", timestamp: "02:14", ai_generated: false },
        { message_id: "m2", sender_type: "AI", message_text: "Sorry 😊 Pink color is currently out of stock. I have logged your request for the owner!", timestamp: "02:14", ai_generated: true },
        { message_id: "m3", sender_type: "CUSTOMER", message_text: "brown me 3 piece pack kar do fir", timestamp: "02:15", ai_generated: false }
      ]
    }
  ]);

  const [selectedConvId, setSelectedConvId] = useState<string>("conv-101");
  const [manualReplyText, setManualReplyText] = useState<string>("");

  const selectedConv = conversations.find(c => c.conversation_id === selectedConvId);

  const handleToggleHumanMode = (convId: string) => {
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
          sender_type: "HUMAN" as const,
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
    setManualReplyText("");
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
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
                placeholder="Search orders (#1042), Rahul, bag, blue requests..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full bg-transparent text-white placeholder-gray-500 focus:outline-none text-base"
              />
            </div>
            <div className="p-4 text-xs text-gray-400 flex justify-between">
              <span>Type to search across products, orders & requests</span>
              <span>Press ESC to close</span>
            </div>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <nav className="bg-gray-900/60 border-b border-gray-800 px-6 flex space-x-2">
        {[
          { id: 'dashboard', label: "Tonight's Summary", icon: TrendingUp },
          { id: 'chats', label: "Live Chats & Handoff", icon: MessageSquare, badge: nightlyReport.human_review_queue_count },
          { id: 'orders', label: "Order Fulfillment Center", icon: ShoppingBag, badge: orders.length },
          { id: 'products', label: "Products Admin Window", icon: Package },
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
                <p className="text-sm text-gray-400">Strictly computed from database facts (Free-Host Compatible Caching)</p>
              </div>
              <button className="flex items-center space-x-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 text-sm font-medium rounded-lg border border-gray-700 transition">
                <RefreshCw className="w-4 h-4" />
                <span>Re-verify Facts</span>
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
                <p>• Top Requested Variant: Blue Color (7 requests)</p>
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
                {conversations.map(conv => {
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
                        <span className="font-medium text-white text-sm">Customer #{conv.customer_id}</span>
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
                        {conv.messages[conv.messages.length - 1]?.message_text}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Selected Chat Box */}
            <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-xl flex flex-col overflow-hidden">
              {selectedConv ? (
                <>
                  {/* Chat Header & Human Handoff Controls */}
                  <div className="p-4 border-b border-gray-800 flex justify-between items-center bg-gray-900/80">
                    <div>
                      <h4 className="font-semibold text-white">Customer #{selectedConv.customer_id}</h4>
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
                          ? "Type your message as owner..."
                          : "Type a message (Sending will automatically activate Human Mode)..."
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

        {/* TAB 3: ORDER FULFILLMENT CENTER (V2.0 Card Layout) */}
        {activeTab === 'orders' && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white">Order Fulfillment Center</h2>
            <p className="text-sm text-gray-400">Complete fulfillment details - Everything needed for fast manual Meesho ordering</p>

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
                        href="https://meesho.com/s/p/bag01"
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

                    {/* One-Click Copy Actions for Quick Meesho Fulfillment */}
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
          </div>
        )}

        {/* TAB 4: PRODUCTS & PRICING ADMIN WINDOW */}
        {activeTab === 'products' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold text-white">Product Management Window</h2>
              <button className="px-4 py-2 bg-pink-600 hover:bg-pink-500 text-white text-sm font-semibold rounded-lg flex items-center space-x-1.5 transition">
                <Plus className="w-4 h-4" />
                <span>Add Product</span>
              </button>
            </div>

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
                          key={v.variant_id}
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
          </div>
        )}

        {/* TAB 5: VARIANT REQUESTS */}
        {activeTab === 'requests' && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-white">Customer Variant Requests</h2>
            <p className="text-sm text-gray-400">Automated market demand detection for unstocked colors, sizes, or variants</p>

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
          </div>
        )}
      </main>
    </div>
  );
}
