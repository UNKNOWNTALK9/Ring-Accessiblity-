# ♿ Ring Accessible Alert
### See Every Alert. Miss Nothing.

## About the Project

Hi! I'm the developer of **Ring Accessible Alert**, a project designed to make doorbell and visitor notifications more accessible for deaf and hard-of-hearing people.

Traditional doorbells depend on sound, which can make it difficult for people with hearing loss to know when someone is at their door. I wanted to explore how technology could help solve this problem through clear visual notifications and accessible controls.

My project is a responsive web application built with Python, Flask, SQLite, HTML, CSS, and JavaScript. It provides a working demonstration of accessible alerts and establishes a foundation for a future authorized Ring integration.

## Why I Built This Project

I believe technology should be accessible to everyone. I created this project to explore how smart-home technology can improve everyday life for people with different accessibility needs.

My goal is simple: **help users notice important door activity without depending only on sound.**

## Key Features

- **Visual Alerts:** Clear, prominent notifications for doorbell and visitor events.
- **Real-Time Updates:** Uses Server-Sent Events (SSE) to deliver updates to the web interface.
- **Event History:** Stores events so users can review previous activity.
- **Alert Acknowledgement:** Allows users to mark alerts as acknowledged.
- **Accessibility Settings:** Supports interface customization, including high-contrast and larger-text options.
- **Browser Vibration:** Provides optional vibration where the browser and device support it.
- **Demo Mode:** Generates clearly labeled sample events for testing and presentations.
- **Real Ring Mode:** Provides a separate integration boundary for a future authorized Ring connection.
- **User Authentication:** Supports email/password registration and sign-in.
- **Optional Social Login:** Includes Google, GitHub, and LinkedIn authentication setup options that require provider credentials.
- **CSV Export:** Allows users to export event history.
- **Automation Rules:** Provides a foundation for configurable alert behavior.

## Technologies I Used

### Frontend Layer
- HTML5
- CSS3
- JavaScript

### Backend Layer
- Python
- Flask

### Database Layer
- SQLite

### Authentication and Security
- Authlib
- Werkzeug password hashing
- Flask sessions
- CSRF protection
- Environment variables using `.env`

### Real-Time Communication
- Server-Sent Events (SSE)

### Data Export
- Python CSV module

### Development Tools
- Visual Studio Code
- Git
- GitHub

## How It Works

1. I built the web interface to display accessible notifications.
2. The Flask backend handles application requests and event processing.
3. SQLite stores event history and application settings.
4. Server-Sent Events deliver updates to the connected interface.
5. Users can acknowledge alerts, adjust accessibility settings, and export event history.
6. Demo Mode allows me to demonstrate the workflow without Ring hardware.

**Important:** Demo Mode uses synthetic events. A real Ring device is not automatically connected by selecting Real Mode. Actual Ring event integration requires an approved API or SDK, appropriate permissions, and a completed and tested adapter.

## Installation and Setup

### Requirements
- Python 3.10 or newer
- A modern web browser
- Git (optional)

### Steps

1. Clone or download my project.
2. Open the project folder in a terminal.
3. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```

   On Windows:

   ```powershell
   .venv\Scripts\activate
   ```

4. Install the required libraries:

   ```bash
   pip install -r requirements.txt
   ```

5. Copy the example environment file:

   ```powershell
   copy .env.example .env
   ```

6. Open `.env` and configure a strong `FLASK_SECRET_KEY`. Keep authentication enabled and never publish secrets to GitHub.

7. Start the application:

   ```bash
   python app.py
   ```

8. Open `http://127.0.0.1:5000/register` in your browser, create an account, and sign in.

Follow the project's configuration instructions if you want to enable an OAuth provider.

## Testing

To run the project's automated tests, use:

```bash
python -m unittest discover -s tests -v
```

## Challenges I Worked On

During development, I focused on making the interface accessible, organizing the backend and database, handling real-time updates, and separating simulated events from genuine device events.

I also worked on authentication, application configuration, and database initialization to make the prototype more reliable.

## What I Learned

Building this project helped me develop my skills in:

- Python backend development with Flask
- Frontend development with HTML, CSS, and JavaScript
- SQLite database management
- Real-time web communication
- Authentication and secure configuration
- Accessibility-focused interface design
- Project organization and testing

## Future Improvements

I would like to improve the project by adding:

- An authorized Ring API/SDK integration
- Mobile push notifications
- Smart-display notifications
- More customizable alert priorities
- Additional languages and accessibility options
- Improved offline handling
- Testing with assistive technologies and accessibility guidelines

## Current Project Status

This project is a **hackathon prototype** with a functional demo workflow. Real Ring device connectivity and social login require their respective integrations, permissions, and credentials.

I aim to develop the project further while keeping accessibility, privacy, and honest reporting of implemented features at the center of the design.

## My Goal

Through Ring Accessible Alert, I want to demonstrate how software can make everyday technology more inclusive and help people access important notifications in ways that work for them.

**Built with accessibility in mind. Developed to make smart-home alerts more inclusive.**

