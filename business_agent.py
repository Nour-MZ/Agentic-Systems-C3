import os
import json
import gradio as gr
from datetime import datetime
from typing import List, Dict, Any
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
                        "description": "Record a customer lead when someone shows interest in EcoTech services.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "name": {"type": "STRING", "description": "The customer's name"},
                                "email": {"type": "STRING", "description": "The customer's email address"},
                                "message": {"type": "STRING", "description": "The customer's message or specific interest"}
                            },
                            "required": ["email", "name"]
                        }
                    },
                    {
                        "name": "record_feedback", 
                        "description": "Record unanswered questions or feedback for follow-up by the team.",
                        "parameters": {
                            "type": "OBJECT", 
                            "properties": {
                                "question": {"type": "STRING", "description": "The unanswered question or feedback"}
                            },
                            "required": ["question"]
                        }
                    }
                ]
            }
        ]
        
        # Initialize model with updated model name
        self.model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',  # Updated to current model
            tools=self.tools
        )
        
        # Load business context
        self.business_context = self._load_business_context()
        
        # Initialize storage
        self.leads = []
        self.feedback = []
        
        # Load existing data
        self._load_existing_data()
    
    def _load_business_context(self) -> str:
        """Load business information from files"""
        try:
            with open('me/business_summary.txt', 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return "EcoTech Innovations - Sustainable AI Solutions Provider"
    
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
    
    def record_customer_interest(self, name: str, email: str, message: str) -> str:
        """Tool to record customer leads"""
        lead_data = {
            'name': name,
            'email': email, 
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'status': 'new'
        }
        
        self.leads.append(lead_data)
        
        print(f"🎯 NEW LEAD CAPTURED:")
        print(f"   Name: {name}")
        print(f"   Email: {email}")
        print("-" * 50)
        
        with open('leads.json', 'w') as f:
            json.dump(self.leads, f, indent=2)
            
        return f"Thank you {name}! We've received your interest and will contact you at {email} shortly."
    
    def record_feedback(self, question: str) -> str:
        """Tool to record unanswered questions"""
        feedback_data = {
            'question': question,
            'timestamp': datetime.now().isoformat(), 
            'status': 'unanswered'
        }
        
        self.feedback.append(feedback_data)
        
        print(f"❓ UNANSWERED QUESTION: {question}")
        print("-" * 50)
        
        with open('feedback.json', 'w') as f:
            json.dump(self.feedback, f, indent=2)
            
        return f"We've noted your question about '{question}'. Our team will research this and get back to you."
    
    def get_system_instruction(self) -> str:
        """Create the system instruction for the business agent"""
        return f"""
        You are the official AI assistant for EcoTech Innovations. 
        BUSINESS CONTEXT: {self.business_context}
        
        Use record_customer_interest when users provide contact info or show business interest.
        Use record_feedback when you cannot answer a question properly.
        """
    
    def process_message(self, message: str, history: List) -> str:
        """Process user message using Gemini function calling"""
        try:
            conversation = []
            
            # Add system instruction
            conversation.append({
                "role": "user", 
                "parts": [{"text": self.get_system_instruction()}]
            })
            conversation.append({
                "role": "model",
                "parts": [{"text": "Understood. I'm ready to assist as the EcoTech Innovations business assistant."}]
            })
            
            # Add recent chat history
            for user_msg, bot_msg in history[-4:]:
                conversation.extend([
                    {"role": "user", "parts": [{"text": user_msg}]},
                    {"role": "model", "parts": [{"text": bot_msg}]}
                ])
            
            # Add current message
            conversation.append({
                "role": "user",
                "parts": [{"text": message}]
            })
            
            # Generate response
            response = self.model.generate_content(conversation)
            
            # Check for function calls
            if response.candidates and response.candidates[0].content.parts:
                first_part = response.candidates[0].content.parts[0]
                
                if hasattr(first_part, 'function_call') and first_part.function_call:
                    function_call = first_part.function_call
                    function_name = function_call.name
                    args = dict(function_call.args)
                    
                    print(f"🔧 FUNCTION CALL: {function_name}")
                    
                    if function_name == "record_customer_interest":
                        return self.record_customer_interest(
                            name=args.get('name', 'Interested Client'),
                            email=args.get('email'),
                            message=args.get('message', 'General inquiry')
                        )
                    elif function_name == "record_feedback":
                        return self.record_feedback(
                            question=args.get('question', message)
                        )
            
            return response.text
            
        except Exception as e:
            print(f"Error in process_message: {e}")
            return "I apologize for the technical difficulty. Please try again."

    def get_stats(self) -> Dict[str, int]:
        """Get business statistics"""
        return {
            "total_leads": len(self.leads),
            "total_feedback": len(self.feedback),
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
        response = agent.process_message(message, history)
        return response
    except Exception as e:
        return f"I apologize for the error. Please try again."

def create_gradio_app():
    """Create and configure the Gradio interface"""
    with gr.Blocks(title="EcoTech Innovations Assistant", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🌱 EcoTech Innovations Assistant")
        
        # Fixed ChatInterface with type="messages"
        chatbot = gr.ChatInterface(
            fn=chat_interface,
            type="messages",  # This fixes the deprecation warning
            title="EcoTech Business Assistant",
            description="Ask me about our sustainable technology services!",
            examples=[
                "What services do you offer?",
                "How can you help reduce carbon emissions?",
                "Here's my email: example@company.com - please contact me"
            ]
        )
        
    return demo