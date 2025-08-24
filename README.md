# Advanced Customer Relationship Manager with AI Chatbot

## Overview

This is a Flask-based web application designed for managing customer relationships, enhanced with an AI-powered chatbot and 3D animations inspired by [Anime.js](https://animejs.com/). The application allows users to manage customer data, track interactions, generate AI-driven insights, export data as CSV, and interact with a context-aware AI chatbot for customer queries and general CRM assistance. The UI features dynamic 3D animations for a modern, engaging experience.

## Features

### Customer Management
- Add, edit, delete, and search customers by name, account, email, or phone.
- Store customer data (ID, name, account, email, phone, creation, and update timestamps) in an SQLite database.
- Sort customer table by columns with a JavaScript-based sorting function.

### Interactions Tracking
- Record and manage interaction notes for each customer with timestamps.
- View and delete interaction history.

### AI-Powered Insights
- Generate personalized business insights for customers using the Groq AI API.
- Save AI insights as interaction notes.
- Custom query option for specific customer-related questions.

### AI Chatbot
- Floating chat interface for real-time interaction with a Groq-powered AI assistant.
- Context-aware responses using customer data and recent interactions.
- Chat history stored in the database and displayed in the UI (last 5 messages).

### 3D Animations
- Scroll-triggered 3D animations using Anime.js for customer table rows (`translateZ`, `rotateX`) and buttons (`translateZ`, `rotateY`).
- Smooth hover effects and responsive design for an engaging UI.

### Data Export
- Export customer data to CSV for external use.

## Prerequisites
- **Python 3.8+**: Ensure Python is installed on your system.
- **Flask**: Web framework for the application (`pip install flask`).
- **Groq Python SDK**: For AI-powered features (`pip install groq`).
- **SQLite**: Included with Python, no separate installation needed.
- **Internet Connection**: Required for CDN-hosted dependencies (Bootstrap, Anime.js, Bootstrap Icons).
- **Groq API Key**: Obtain from [xAI](https://x.ai/api).

## Setup Instructions
1. **Clone the Repository** (or save the file as `app.py`):
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```
   If you’re not using a repository, copy the `app.py` file to your project directory.

2. **Set Up a Virtual Environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install flask groq
   ```

4. **Obtain a Groq API Key**:
   - Sign up at [xAI](https://x.ai/api) to get a Groq API key.
   - The app will prompt you to enter the API key on first run via the web interface.

## How to Run the Application
1. **Ensure Dependencies Are Installed**:
   - Verify that Flask and Groq are installed by running:
     ```bash
     pip show flask groq
     ```
   - If not installed, refer to the Setup Instructions above.

2. **Save the Code**:
   - Ensure the application code is saved as `app.py` in your project directory.

3. **Run the Flask Application**:
   - Open a terminal in the project directory and run:
     ```bash
     python app.py
     ```
   - This starts the Flask development server in debug mode, accessible at `http://localhost:5000`.

4. **Access the Application**:
   - Open a web browser and navigate to `http://localhost:5000`.
   - If prompted, enter your Groq API key to initialize the app. The key is stored in the SQLite database (`crm.db`) for subsequent runs.

5. **Optional: Run on a Specific Host/Port**:
   - To run on a different host or port (e.g., for network access), modify the `app.run` line in `app.py` or use command-line arguments:
     ```bash
     python app.py --host=0.0.0.0 --port=8080
     ```
   - Update `app.run(debug=True)` to `app.run(host='0.0.0.0', port=8080, debug=True)` in `app.py` for persistent changes.

6. **Stop the Application**:
   - Press `Ctrl+C` in the terminal to stop the Flask server.

## Usage
### Customer Management
- Add a new customer using the form (name and account are required).
- Search customers using the search bar.
- Edit or delete customers via the action buttons.
- Sort the table by clicking column headers.

### Interactions
- Click "View/Add" in the Interactions column to add or view notes for a customer.
- Delete interactions as needed.

### AI Insights
- Click "Generate" in the AI Insight column to get personalized suggestions.
- Use the custom query form for specific questions about a customer.
- Save insights as interaction notes.

### AI Chatbot
- Click the chat icon (bottom-right) to open the chat window.
- Ask about customers (e.g., "Details for customer John") or general CRM queries (e.g., "How to manage customer data").
- Press Enter or click Send to submit messages.
- View recent chat history in the chat window.

### Export Data
- Click "Export CSV" to download customer data.

### Animations
- Scroll through the customer table to see 3D animations (rows and buttons slide in with rotations).
- Hover over buttons for additional visual effects.

## Project Structure
- `app.py`: The main Flask application file containing all routes, templates, and logic.
- `crm.db`: SQLite database (created automatically) storing customers, interactions, chat history, and configuration (API key).

## Dependencies
- **Flask**: Web framework for routing and templating.
- **Groq**: AI API for generating insights and powering the chatbot.
- **SQLite**: Lightweight database for data storage.
- **Bootstrap 5.3.3** (via CDN): Styling and responsive UI components.
- **Anime.js 3.2.1** (via CDN): 3D scroll animations.
- **Bootstrap Icons** (via CDN): Icons for UI elements.

## Notes
- **API Key Security**: Store your Groq API key securely. The app stores it in the SQLite database (`config` table) for convenience, but consider environment variables for production.
- **Internet Dependency**: The app uses CDNs for Bootstrap, Anime.js, and Bootstrap Icons. For offline use, host these files locally in a Flask static folder.
- **Responsive Design**: The UI, including the chatbot, is optimized for mobile and desktop devices.
- **Performance**: The chatbot limits context to recent data (last 10 interactions, last 5 chat messages in UI) to ensure fast responses.
- **Extensibility**: Add animations or chatbot functionality to other pages (e.g., `/insight`, `/interactions`) by extending the relevant templates.

## Troubleshooting
- **API Key Issues**: Ensure a valid Groq API key is entered. Check [xAI API](https://x.ai/api) for details.
- **Animations Not Working**: Verify internet connectivity for Anime.js CDN or host the library locally.
- **Database Errors**: If `crm.db` is corrupted, delete it and restart the app to recreate it.
- **Chatbot Errors**: Ensure the Groq API is accessible and the key is valid.
- **Port Conflicts**: If port 5000 is in use, change the port in `app.run` or terminate the conflicting process.

## Future Enhancements
- Add 3D animations to other pages (e.g., `/insight`, `/interactions`).
- Implement chat history pagination or clearing.
- Add user authentication for secure access.
- Enhance chatbot with conversation memory or more advanced context handling.

## License
This project is licensed under the MIT License.

## Acknowledgments
- [Anime.js](https://animejs.com/) for 3D animation capabilities.
- [Groq](https://x.ai/) for AI-powered insights and chatbot functionality.
- [Bootstrap](https://getbootstrap.com/) for responsive UI design.
