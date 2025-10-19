import os
import json
import re
import gradio as gr
from datetime import datetime
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EnhancedBusinessAgent:
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Please set GOOGLE_API_KEY in your .env file")
        
        genai.configure(api_key=self.api_key)
        
        # Define tools (functions) for the model
        self.tools = [
            {
                "function_declarations": [
                    {
                        "name": "record_customer_interest",
                        "description": "Record a customer lead when someone shows interest in Nexus Creative Labs services. Use when user provides contact information or explicitly asks to be contacted.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "name": {
                                    "type": "STRING",
                                    "description": "The customer's name"
                                },
                                "email": {
                                    "type": "STRING", 
                                    "description": "The customer's email address"
                                },
                                "message": {
                                    "type": "STRING",
                                    "description": "The customer's project interest or inquiry"
                                }
                            },
                            "required": ["email"]
                        }
                    },
                    {
                        "name": "record_feedback",
                        "description": "Record unanswered questions or feedback for follow-up by the team. Use when you cannot answer a question properly or user provides feedback.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "question": {
                                    "type": "STRING",
                                    "description": "The unanswered question or feedback"
                                }
                            },
                            "required": ["question"]
                        }
                    }
                ]
            }
        ]
        
        # Initialize model with tools
        self.model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            tools=self.tools
        )
        
        # Load business context
        self.business_context = self._load_business_context()
        
        # Initialize storage
        self.leads = []
        self.feedback = []
        
        # Context tracking for multi-message lead capture
        self.pending_leads = {}  # Tracks incomplete lead information
        
        # Load existing data
        self._load_existing_data()
    
    def _load_business_context(self) -> str:
        """Load business information from files"""
        try:
            with open('me/business_summary.txt', 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return "Nexus Creative Labs - Bridging Imagination and Innovation"
    
    def _load_existing_data(self):
        """Load existing leads and feedback from files"""
        try:
            with open('leads.json', 'r') as f:
                self.leads = json.load(f)
        except FileNotFoundError:
            self.leads = []
            
        try:
            with open('feedback.json', 'r') as f:
                self.feedback = json.load(f)
        except FileNotFoundError:
            self.feedback = []
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email from text using regex"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        return match.group() if match else None
    
    def _extract_name(self, text: str) -> Optional[str]:
        """Extract potential name from text"""
        # Look for patterns like "my name is", "I'm", "call me"
        patterns = [
            r'(?:my name is|I\'m|call me|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)$'  # Just a name by itself
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _update_pending_lead(self, user_id: str, name: str = None, email: str = None, message: str = None):
        """Update pending lead information across multiple messages"""
        if user_id not in self.pending_leads:
            self.pending_leads[user_id] = {'name': None, 'email': None, 'message': None}
        
        if name:
            self.pending_leads[user_id]['name'] = name
        if email:
            self.pending_leads[user_id]['email'] = email
        if message:
            self.pending_leads[user_id]['message'] = message
    
    def _get_pending_lead(self, user_id: str) -> Dict[str, str]:
        """Get current pending lead information"""
        return self.pending_leads.get(user_id, {'name': None, 'email': None, 'message': None})
    
    def _is_lead_complete(self, user_id: str) -> bool:
        """Check if we have enough information to create a lead"""
        lead = self._get_pending_lead(user_id)
        return lead['email'] is not None and (lead['name'] or lead['message'])
    
    def record_customer_interest(self, name: str, email: str, message: str, user_id: str = "default") -> str:
        """Tool to record customer leads with context awareness"""
        # Use pending lead data to fill missing information
        pending_data = self._get_pending_lead(user_id)
        
        final_name = name or pending_data['name'] or "Interested Client"
        final_email = email or pending_data['email']
        final_message = message or pending_data['message'] or "General inquiry about creative services"
        
        if not final_email:
            return "I'd love to help you! Could you please provide your email address so our team can contact you?"
        
        lead_data = {
            'name': final_name,
            'email': final_email,
            'message': final_message,
            'timestamp': datetime.now().isoformat(),
            'status': 'new',
            'user_id': user_id
        }
        
        self.leads.append(lead_data)
        
        print(f"🎯 NEW LEAD CAPTURED:")
        print(f"   Name: {final_name}")
        print(f"   Email: {final_email}")
        print(f"   Project: {final_message}")
        print(f"   Timestamp: {lead_data['timestamp']}")
        print("-" * 50)
        
        # Save to file
        with open('leads.json', 'w') as f:
            json.dump(self.leads, f, indent=2)
        
        # Clear pending lead for this user
        if user_id in self.pending_leads:
            del self.pending_leads[user_id]
            
        return f"Thank you {final_name}! We've received your interest in '{final_message}' and will contact you at {final_email} within 24 hours. Our creative director will reach out to discuss your vision!"
    
    def record_feedback(self, question: str) -> str:
        """Tool to record unanswered questions"""
        feedback_data = {
            'question': question,
            'timestamp': datetime.now().isoformat(),
            'status': 'unanswered'
        }
        
        self.feedback.append(feedback_data)
        
        print(f"❓ UNANSWERED QUESTION:")
        print(f"   Question: {question}")
        print(f"   Timestamp: {feedback_data['timestamp']}")
        print("-" * 50)
        
        # Save to file
        with open('feedback.json', 'w') as f:
            json.dump(self.feedback, f, indent=2)
            
        return f"We've noted your question about '{question}'. Our creative team will research this and include insights in our follow-up. Thank you for pushing our boundaries!"
    
    def get_system_instruction(self) -> str:
        """Create the system instruction for the business agent"""
        return f"""
        You are the official AI assistant for Nexus Creative Labs. Your role is to represent our innovative creative studio and help potential clients.

        BUSINESS CONTEXT:
        {self.business_context}

        YOUR RESPONSIBILITIES:
        1. Answer questions about our immersive experiences, creative technology, and design services
        2. Be inspiring, creative, and professional in all interactions
        3. Use the record_customer_interest function when:
           - User provides their email address
           - User shows interest in a specific project or service
           - User asks to be contacted by our team
        4. Use the record_feedback function when:
           - You cannot answer a technical or creative question
           - User asks about emerging technologies beyond current expertise
        5. Always stay in character as the Nexus Creative Labs assistant

        CONTEXT-AWARE LEAD CAPTURE:
        - If user provides information across multiple messages (name, then email, then project details), track this context
        - When enough information is gathered (especially email), trigger lead capture
        - Be natural in conversation while gathering necessary information

        GUIDELINES:
        - Focus on creative possibilities and innovative solutions
        - Share relevant project examples and case studies
        - Be curious about the user's creative vision
        - If asked about pricing, explain we provide custom quotes based on project scope

        Remember: You are the first point of contact for an innovative creative studio. Be inspiring, knowledgeable, and genuinely interested in the user's creative ideas.
        """
    
    def process_message(self, message: str, history: List, user_id: str = "default") -> str:
        """Process user message with context-aware lead capture"""
        try:
            # Extract potential lead information from current message
            extracted_email = self._extract_email(message)
            extracted_name = self._extract_name(message)
            
            # Update pending lead with extracted information
            if extracted_name or extracted_email or any(word in message.lower() for word in ['project', 'interested', 'help with', 'looking for']):
                self._update_pending_lead(
                    user_id, 
                    name=extracted_name,
                    email=extracted_email,
                    message=message if len(message) > 10 and not extracted_email else None
                )
            
            # Prepare conversation history
            conversation = []
            
            # Add system instruction
            conversation.append({
                "role": "user",
                "parts": [{"text": self.get_system_instruction()}]
            })
            conversation.append({
                "role": "model", 
                "parts": [{"text": "Understood. I'm ready to inspire and assist as the Nexus Creative Labs assistant."}]
            })
            
            # Add recent chat history (last 6 exchanges for better context)
            for user_msg, bot_msg in history[-6:]:
                conversation.extend([
                    {"role": "user", "parts": [{"text": user_msg}]},
                    {"role": "model", "parts": [{"text": bot_msg}]}
                ])
            
            # Add current message
            conversation.append({
                "role": "user", 
                "parts": [{"text": message}]
            })
            
            # Check if we have enough information to suggest lead capture
            pending_lead = self._get_pending_lead(user_id)
            if self._is_lead_complete(user_id) and not any(tool in message.lower() for tool in ['record', 'capture', 'lead']):
                # Add hint to the model that we have lead information
                conversation.append({
                    "role": "user",
                    "parts": [{"text": f"CONTEXT: We have collected lead information - Name: {pending_lead['name'] or 'Not provided'}, Email: {pending_lead['email']}, Interest: {pending_lead['message'] or 'Not specified'}. Consider using record_customer_interest if appropriate."}]
                })
            
            # Generate response with function calling
            response = self.model.generate_content(conversation)
            
            # Check if function calling was triggered
            if response.candidates and response.candidates[0].content.parts:
                first_part = response.candidates[0].content.parts[0]
                
                if hasattr(first_part, 'function_call') and first_part.function_call:
                    function_call = first_part.function_call
                    function_name = function_call.name
                    args = dict(function_call.args)
                    
                    print(f"🔧 FUNCTION CALL: {function_name} with args: {args}")
                    
                    # Execute the appropriate function
                    if function_name == "record_customer_interest":
                        result = self.record_customer_interest(
                            name=args.get('name'),
                            email=args.get('email'),
                            message=args.get('message'),
                            user_id=user_id
                        )
                        return result
                    
                    elif function_name == "record_feedback":
                        result = self.record_feedback(
                            question=args.get('question', message)
                        )
                        return result
            
            # If no function call but we have email, check if we should capture lead
            if extracted_email and not any(fc in str(response) for fc in ['record_customer_interest', 'record_feedback']):
                # If user provided email and seems interested, capture lead
                if any(word in message.lower() for word in ['contact', 'email', 'reach', 'call', 'talk']):
                    return self.record_customer_interest(
                        name=extracted_name,
                        email=extracted_email,
                        message=pending_lead.get('message', 'Contact request'),
                        user_id=user_id
                    )
            
            # Return the text response
            return response.text
            
        except Exception as e:
            print(f"Error in process_message: {e}")
            return "I apologize, but I'm experiencing creative block (technical difficulties). Please try again or contact us directly at hello@nexuscreativelabs.com."

    def get_stats(self) -> Dict[str, int]:
        """Get business statistics"""
        return {
            "total_leads": len(self.leads),
            "total_feedback": len(self.feedback),
            "pending_leads": len(self.pending_leads),
            "new_leads_today": len([
                lead for lead in self.leads 
                if datetime.fromisoformat(lead['timestamp']).date() == datetime.now().date()
            ])
        }


# Global agent instance
agent = EnhancedBusinessAgent()

def chat_interface(message: str, history: List) -> str:
    """Gradio chat interface function"""
    try:
        # For demo purposes, using session-based user_id
        # In production, you'd use Gradio's user session tracking
        user_id = "user_001"
        response = agent.process_message(message, history, user_id)
        return response
    except Exception as e:
        return f"I apologize for the creative interruption. Please try again."

def create_gradio_app():
    """Create and configure the Gradio interface"""
    with gr.Blocks(
        title="Nexus Creative Labs Assistant",
        theme=gr.themes.Soft(),
        css="""
        .gradio-container {
            max-width: 800px;
            margin: 0 auto;
        }
        .creative-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 10px;
            color: white;
            margin-bottom: 20px;
        }
        """
    ) as demo:
        gr.Markdown(
            """
            <div class="creative-header">
            <h1>🚀 Nexus Creative Labs Assistant</h1>
            <p><em>Where Imagination Meets Innovation</em></p>
            </div>
            """
        )
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📊 Studio Stats")
                stats = agent.get_stats()
                gr.Markdown(f"""
                - **Active Projects**: {stats['total_leads']}
                - **Creative Inquiries**: {stats['total_feedback']}
                - **New Today**: {stats['new_leads_today']}
                - **In Progress**: {stats['pending_leads']}
                """)
                
                gr.Markdown("""
                ### 🎯 How We Can Help
                - Immersive AR/VR Experiences
                - Interactive Installations  
                - Creative AI Solutions
                - Digital Storytelling
                - Rapid Prototyping
                """)
            
            with gr.Column(scale=2):
                # Chat interface with updated examples
                chatbot = gr.ChatInterface(
                    fn=chat_interface,
                    type="messages",
                    title="Chat with Our Creative Assistant",
                    description="Tell me about your creative vision! I can help with project inquiries, technical questions, or connect you with our team.",
                    examples=[
                        "I'm interested in creating an AR experience for my brand",
                        "My name is Alex and I have a project idea",
                        "Here's my email: creator@studio.com - I'd like to discuss VR",
                        "What's your process for interactive installations?",
                        "Can you help with AI-generated art for an exhibition?",
                        "I need prototyping for a creative tech product"
                    ]
                )
        
        gr.Markdown(
            """
            ---
            **🎨 Studio Locations**: Brooklyn, NY & Tokyo, Japan  
            **📧 Email**: hello@nexuscreativelabs.com  
            **🌐 Portfolio**: www.nexuscreativelabs.com
            **💼 Follow Us**: @NexusCreativeLabs on socials
            """
        )
        
    return demo