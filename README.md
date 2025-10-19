# SwinSACA - AI-Guided Medical Triage System

SwinSACA is an AI-powered medical triage system designed to provide accessible healthcare guidance, with special support for Indigenous languages including Arrernte. The system combines natural language processing, medical knowledge, and cultural sensitivity to help users assess their health concerns.

## Features

### 🤖 AI Medical Assistant
- Intelligent symptom assessment and triage
- Multi-turn conversation support
- Medical condition recognition
- Severity level assessment (1-5 scale)
- Personalized health recommendations

### 🌍 Multilingual Support
- English and Arrernte language support
- Real-time translation capabilities
- Audio pronunciation for Arrernte words
- Cultural context awareness

### 🎯 Multiple Interaction Modes
- **Text Mode**: Traditional chat interface
- **Voice Mode**: Speech-to-text and text-to-speech
- **Images Mode**: Visual symptom selection interface

### 🔒 Security & Privacy
- JWT-based authentication
- Secure user data handling
- HIPAA-compliant design principles

## Technology Stack

### Backend
- **Flask**: Web framework
- **PyTorch**: Deep learning for NLP
- **NLTK**: Natural language processing
- **SQLAlchemy**: Database ORM
- **JWT**: Authentication
- **Faster-Whisper**: Speech recognition
- **RapidFuzz**: Fuzzy string matching

### Frontend
- **React**: User interface framework
- **TypeScript**: Type-safe JavaScript
- **Chakra UI**: Component library
- **React Router**: Navigation
- **Vite**: Build tool

## Quick Start

### Prerequisites
- Python 3.8 or higher
- Node.js 16 or higher
- npm or yarn

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd swinsaca
   ```

2. **Run the setup script**
   ```bash
   python setup.py
   ```

   This will:
   - Install all Python dependencies
   - Install all Node.js dependencies
   - Download required NLTK data
   - Create environment configuration
   - Generate start scripts

3. **Start the application**

   **Option A: Using start scripts**
   ```bash
   # Terminal 1 - Backend
   start_backend.bat    # Windows
   ./start_backend.sh   # Linux/Mac
   
   # Terminal 2 - Frontend
   start_frontend.bat   # Windows
   ./start_frontend.sh  # Linux/Mac
   ```

   **Option B: Manual start**
   ```bash
   # Terminal 1 - Backend
   cd "Backend & NLP"
   python app.py
   
   # Terminal 2 - Frontend
   cd Frontend
   npm run dev
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5000
   - API Documentation: http://localhost:5000/apidocs/

## Project Structure

```
swinsaca/
├── Backend & NLP/           # Backend application
│   ├── app.py              # Main Flask application
│   ├── models.py           # Database models
│   ├── routes.py           # API routes
│   ├── requirements.txt    # Python dependencies
│   ├── Chatbot/            # AI chatbot module
│   │   ├── chat.py         # Main chatbot logic
│   │   ├── model.py        # Neural network model
│   │   ├── intents.json    # Training data
│   │   └── data.pth        # Trained model
│   └── Glossary/           # Translation module
│       ├── glossary_translator.py
│       └── arrernte_audio.csv
├── Frontend/               # React frontend
│   ├── app/                # Application code
│   │   ├── routes/         # Page components
│   │   ├── components/     # Reusable components
│   │   └── utils/          # Utility functions
│   ├── package.json        # Node.js dependencies
│   └── vite.config.ts      # Build configuration
├── setup.py                # Setup script
└── README.md               # This file
```

## API Endpoints

### Chat Endpoints
- `POST /api/chat/` - Main chat interface
- `GET /health` - Health check

### Translation Endpoints
- `POST /api/translate/to_arrernte` - English to Arrernte
- `POST /api/translate/to_english` - Arrernte to English

### Authentication Endpoints
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout

## Usage Examples

### Chat API
```bash
curl -X POST http://localhost:5000/api/chat/ \
  -H "Content-Type: application/json" \
  -H "X-Language: english" \
  -d '{"message": "I have a headache"}'
```

### Translation API
```bash
curl -X POST http://localhost:5000/api/translate/to_arrernte \
  -H "Content-Type: application/json" \
  -d '{"text": "I have a headache"}'
```

## Configuration

### Environment Variables
Create a `.env` file in the `Backend & NLP` directory:

```env
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=jwt-secret-string
DATABASE_URL=sqlite:///swinsaca.db
WHISPER_MODEL=base.en
```

### Language Configuration
The system supports multiple languages through the `X-Language` header:
- `english` - English language
- `arrernte` - Arrernte language
- `arr+english` - Mixed mode

## Development

### Backend Development
```bash
cd "Backend & NLP"
pip install -r requirements.txt
python app.py
```

### Frontend Development
```bash
cd Frontend
npm install
npm run dev
```

### Running Tests
```bash
# Backend tests
cd "Backend & NLP"
python -m pytest

# Frontend tests
cd Frontend
npm test
```

## Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Areas for Contribution
- Additional language support
- Medical knowledge expansion
- UI/UX improvements
- Performance optimizations
- Documentation improvements

## Medical Disclaimer

⚠️ **Important**: SwinSACA is designed for educational and informational purposes only. It is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of qualified healthcare providers with questions about medical conditions.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Contact: support@swinsaca.org
- Documentation: https://docs.swinsaca.org

## Acknowledgments

- Indigenous language communities for their guidance
- Medical professionals for their expertise
- Open source contributors
- The broader healthcare technology community

---

**SwinSACA** - Bridging healthcare accessibility through AI and cultural sensitivity.
