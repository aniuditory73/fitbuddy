# FitBuddy2 - Telegram Bot

FitBuddy2 is a Telegram bot designed to help users manage their workouts, track progress, and get exercise recommendations.

## Features

*   **Workout Management**: Create, edit, and delete workout plans.
*   **Exercise Database**: Access a comprehensive database of exercises with descriptions and images.
*   **Progress Tracking**: Log your workouts and track your progress over time.
*   **Personalized Recommendations**: Get exercise recommendations based on your goals and preferences.
*   **User Authentication**: Secure user authentication and data storage.

## Installation

To set up FitBuddy2, follow these steps:

### Prerequisites

*   Python 3.9 or higher
*   Telegram Bot API token

### Setup Steps

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/FitBuddy2.git
    cd FitBuddy2
    ```
2.  **Create a virtual environment (optional but recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\\Scripts\\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure the bot:**
    Rename `config_example.py` to `config.py` and update it with your Telegram Bot API token and other necessary configurations.

    ```python
    # config.py
    BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
    ADMIN_ID = YOUR_ADMIN_TELEGRAM_ID
    ```

5.  **Initialize the database:**
    Run the script to set up the SQLite database.
    ```bash
    python database.py
    ```

6.  **Run the bot:**
    ```bash
    python main.py
    ```

## Usage

Once the bot is running, you can interact with it on Telegram:

*   **Start the bot**: Send `/start` to the bot.
*   **Explore exercises**: Use the inline keyboard or commands to browse exercises.
*   **Create a workout**: Follow the bot's prompts to build your personalized workout plan.
*   **Log your progress**: Record your sets, reps, and weight for each exercise.

## Project Structure

*   `main.py`: Main bot application file.
*   `handlers.py`: Contains all message and callback handlers.
*   `database.py`: Handles database interactions (SQLite).
*   `utils.py`: Utility functions and helper classes.
*   `config.py`: Configuration settings (API tokens, admin IDs, etc.).
*   `execercises.json`: JSON file containing exercise data.
*   `exercise_data/images/`: Stores exercise images.
*   `requirements.txt`: Project dependencies.

## Contributing

Contributions are welcome! Please feel free to fork the repository, create a new branch, and submit a pull request with your improvements.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.


