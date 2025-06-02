# AIdea Lab

AIdea Lab is a workshop-style application where various AI persona agents analyze and provide feedback on user ideas from their respective perspectives when users input their ideas.

## Installation Guide

### 1. Clone Project and Set Up Virtual Environment

```bash
# Clone repository (if git repository exists)
# git clone https://github.com/mash1384/aidea-lab.git
# cd aidea-lab

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 2. Install Required Libraries

```bash
pip install -r requirements.txt
```

### 3. Run Application

```bash
streamlit run src/ui/app.py
```

### 4. Google API Key Setup

After running the application, set up your API key in the web browser as follows:

1. **Enter API Key in Sidebar**: 
   - Find the "🔑 Google API Key Setup" section in the left sidebar of the application.
   - Enter your API key in the "Enter Google API Key" field.
   - Click the "🔐 Apply API Key" button.

2. **API Key Generation**:
   - You can obtain a Gemini API key from [Google AI Studio](https://makersuite.google.com/) or [Google Cloud Console](https://console.cloud.google.com/).

3. **API Key Verification**:
   - When the API key is correctly set up, a green checkmark (✅) will be displayed in the sidebar.
   - If there are issues with the setup, a red X mark (❌) along with an error message will be displayed.

⚠️ **Warning**: AI analysis features cannot be used without an API key. Attempting to use LLM features will display a message requesting API key setup.

## How to Use

1. **Enter Idea**: Input the idea you want to analyze in the chat input field at the bottom of the main screen.
2. **Enter Detailed Information (Optional)**: Click the "Enter Idea Details" button to additionally input goals, constraints, values, etc.
3. **Phase 1 Analysis**: AI personas (Marketer, Critical Analyst, Realistic Engineer) analyze the idea from their respective perspectives.
4. **Phase 2 Discussion (Optional)**: After completing Phase 1, click the "💬 Start Phase 2 Discussion" button to proceed with in-depth discussion among AI personas.

## Environment Variable Setup (Optional)

If you want to set a default API key, you can configure one of the following environment variables:

```bash
# Default for user input (higher priority)
GOOGLE_API_KEY_USER_INPUT="YOUR_ACTUAL_API_KEY"

# Or default environment variable
GOOGLE_API_KEY="YOUR_ACTUAL_API_KEY"
```

However, **the recommended approach is to input directly through the sidebar UI after running the application**.

## Running Tests

### 1. Basic ADK Agent Test

```bash
python src/poc/simple_adk_agent.py
```

### 2. Session State Test

```bash
python src/poc/session_state_test_agent.py
```

### 3. API Key Validation Test

```bash
python check_api_key.py
```

## Project Structure

```
aidea-lab/
├── .env                    # Environment variables configuration file (optional)
├── requirements.txt        # Required libraries
├── README.md               # Project description
├── check_api_key.py        # API key validation test script
├── src/                    # Source code
│   ├── agents/             # AI persona agents
│   ├── orchestrator/       # Orchestrator (workflow agent)
│   ├── ui/                 # User interface
│   │   ├── app.py          # Main Streamlit app
│   │   ├── views.py        # UI rendering functions
│   │   └── state_manager.py # Application state management
│   └── poc/                # Proof of concept test code
├── config/                 # Configuration files
├── tests/                  # Test code
├── docs/                   # Documentation
└── scripts/                # Utility scripts
``` 