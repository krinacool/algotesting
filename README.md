# Shoonya API Option Trading Algo with Dashboard

This project is a comprehensive automated trading system for Nifty 50 and Sensex options using the Shoonya (Finvasia) API. It features a real-time web dashboard for monitoring P&L, managing orders, and configuring strategy parameters on the fly.

## Features

- **Dual Supertrend Strategy**: Momentum-based option buying using Supertrend (7, 2.1) and (10, 1). Supports single or dual confirmation modes.
- **Real-time Dashboard**: Built with Flask and SocketIO for live LTP, P&L, and order tracking.
- **Dynamic Lot Sizes**: Automatically fetches and updates lot sizes for NIFTY and SENSEX from the broker.
- **Risk Management**:
  - Stop Loss (Supertrend based or Max % based).
  - Target Points.
  - Trailing Stop Loss.
- **Trading Modes**: Toggle between **Paper Trading** (simulation) and **Real Trading**.
- **Option Selection**: Select contracts based on target Premium or calculated Delta.
- **Auditory Notifications**: Programmatic beeps on configuration save and trade execution.
- **Optimized Performance**: Token caching and throttled polling to stay within Shoonya API rate limits.

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd shoonya-algo-trading
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration & Usage

1. **Start the Application**:
   ```bash
   python app.py
   ```
2. **Access the Dashboard**:
   Open your browser and navigate to `http://localhost:5000`.

3. **Login Details**:
   - Enter your Shoonya **User ID**, **Password**, **API Key**, and **TOTP Secret**.
   - Note: The TOTP secret is the key used to generate your 2FA codes.

4. **Strategy Settings**:
   - **Instrument**: Select NIFTY or SENSEX.
   - **Strategy Mode**: Choose between individual Supertrend signals or Dual confirmation.
   - **Timeframe**: Select 1, 3, 5, or 15-minute candles.

5. **Trading Settings**:
   - **Trading Mode**: Set to 'Paper' for testing or 'Real' for live execution.
   - **Lots**: Number of lots to trade.
   - **Target/Stoploss**: Define your risk parameters and trailing points.

6. **Operation**:
   - Click **Save Details** first to apply your configuration. (You will hear a beep).
   - Click **Start Algo** to begin the strategy loop.
   - Monitor live trades in the **Order Details** table. (You will hear a beep on new trades).

## Project Structure

- `app.py`: Flask web server and SocketIO handler.
- `engine.py`: Core trading logic and position management.
- `shoonya_helper.py`: Shoonya API wrapper and Greeks calculation.
- `strategy.py`: Technical indicator calculations and signal generation.
- `templates/index.html`: Dashboard frontend.

## Disclaimer

Automated trading involves significant risk. Always test your strategy thoroughly in Paper Trading mode before committing real capital. The authors are not responsible for any financial losses incurred using this software.
