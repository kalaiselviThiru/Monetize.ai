import time
import openai
import logging
from flask import request
import sql
from config import Config

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Ensure OpenAI API key is set correctly
if not Config.OPENAI_API_KEY:
    logging.error("OpenAI API Key is missing! Set it in the config.")
else:
    openai.api_key = Config.OPENAI_API_KEY

def update_openai_key(email, key):
    """
    Update OpenAI API key and validate it.

    Args:
        email (str): User email
        key (str): New OpenAI API key
    Returns:
        bool: True if the key is valid, otherwise raises an error
    """
    sql.update_api_key(email, key)
    Config.OPENAI_API_KEY = key
    openai.api_key = key

    # Test API Key
    try:
        test_response = davinci_003("Test API Key")
        if test_response:
            return True
    except Exception as e:
        logging.error(f"Invalid OpenAI API Key: {e}")
        raise ValueError("API key is invalid!")

def davinci_003(query, temperature=0):
    """Generates a response using OpenAI's text-davinci-003 model"""
    logging.info("Starting text-davinci-003...")

    try:
        start_time = time.time()

        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=query,
            temperature=temperature,
            max_tokens=100,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stop=["|"]
        )

        elapsed_time = time.time() - start_time
        logging.info(f"text-davinci-003 response time: {elapsed_time:.2f} seconds")

        return response["choices"][0]["text"].strip()
    except Exception as e:
        logging.error(f"Error in davinci_003: {e}")
        return "Error generating response."

def gpt_3(message_list, temperature=0.2):
    """Uses OpenAI's GPT-3.5-turbo API to generate a response to a query"""

    logging.info("Starting GPT-3.5-turbo...")

    try:
        start_time = time.time()

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=message_list,
            temperature=temperature
        )

        elapsed_time = time.time() - start_time
        logging.info(f"GPT-3.5-turbo response time: {elapsed_time:.2f} seconds")

        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logging.error(f"GPT-3 API Error: {e}")
        return "Error connecting to GPT-3."

def gpt_with_info(message_list, temperature=1):
    """Uses GPT-3 API with user and portfolio information"""

    email = request.cookies.get('email')
    if not email:
        logging.error("Email not found in request cookies.")
        return "Error: User email not found."

    user_data = sql.get_user_data(email)
    if not user_data or not user_data[1]:
        logging.error("User data retrieval failed.")
        return "Error: User data not found."

    user_data = user_data[1]
    user_info = f"User information: Username: {user_data[0]}, Email: {user_data[1]}, Phone: {user_data[2]}."
    risk_tolerance = f"User's risk tolerance: {user_data[3]}."

    portfolio_data = sql.get_stock_data(email)
    if not portfolio_data or not portfolio_data[1]:
        portfolio_info = "User's portfolio is empty."
    else:
        portfolio_info = "User's portfolio details:"
        for stock in portfolio_data[1]:
            portfolio_info += f" Date: {stock[0]}, Ticker: {stock[1]}, Quantity: {stock[2]}, Start Price: {stock[3]}, End Price: {stock[4]}, Return %: {stock[5]}, Total: {stock[7]}."

    # Add user data and portfolio info to system message
    message_list.insert(0, {
        "role": "system",
        "content": f"You are Monetize.ai, a financial chatbot. {user_info} {risk_tolerance} {portfolio_info} If the user asks to change risk tolerance, confirm the update. If they bought/sold stocks, update their portfolio and provide details on profit/loss."
    })

    return gpt_3(message_list, temperature=temperature)
