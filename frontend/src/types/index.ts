export interface ProductVariant {
  variant_id: string;
  type: string;
  value: string;
  available: boolean;
}

export interface ProductFAQ {
  faq_id: string;
  question: string;
  answer: string;
  verified_by_owner: boolean;
}

export interface Product {
  product_id: string;
  sku: string;
  product_name: string;
  description: string;
  actual_price: number;
  selling_price: number;
  currency: string;
  meesho_url?: string;
  images: string[];
  variants: ProductVariant[];
  faqs: ProductFAQ[];
  active: boolean;
}

export interface Message {
  message_id: string;
  sender_type: 'CUSTOMER' | 'AI' | 'HUMAN' | 'SYSTEM';
  message_text: string;
  timestamp: string;
  ai_generated: boolean;
  intent?: string;
}

export interface Conversation {
  conversation_id: string;
  customer_id: string;
  current_intent?: string;
  language: string;
  requires_human_review: boolean;
  human_review_reason?: string;
  human_mode_active: boolean;
  last_activity_at: string;
  messages: Message[];
}

export interface OrderItem {
  item_id: string;
  product_name: string;
  actual_price: number;
  selling_price: number;
  variant?: string;
  quantity: number;
}

export interface Order {
  order_id: string;
  customer_name: string;
  phone: string;
  house_building: string;
  road_area_colony: string;
  total_selling_price: number;
  total_actual_cost: number;
  expected_margin: number;
  order_state: string;
  created_at: string;
  items: OrderItem[];
}

export interface CustomerRequest {
  request_id: string;
  request_type: string;
  requested_value: string;
  original_message: string;
  status: string;
  created_at: string;
}
