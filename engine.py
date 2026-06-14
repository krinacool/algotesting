import threading
import time
import logging
import pandas as pd
from shoonya_helper import ShoonyaApiHelper
from strategy import get_strategy_signals, find_nearest_option
from datetime import datetime

class TradingEngine:
    def __init__(self):
        self.api = ShoonyaApiHelper()
        self.is_running = False
        self.config = {
            'userid': '',
            'password': '',
            'totp_secret': '',
            'api_key': '',
            'vendor_code': '',
            'imei': 'abc1234',
            'trading_mode': 'Paper',
            'instrument': 'NIFTY',
            'lots': 1,
            'stoploss_type': 'Supertend',
            'max_sl_pct': 10,
            'target_type': 'ON',
            'target_points': 10,
            'trailing_sl': 'OFF',
            'trailing_points': 5,
            'order_type': 'MIS',
            'strike_diff': 1,
            'expiry': 0,
            'start_time': '09:15:00',
            'square_off_time': '15:20:00',
            'st_length1': 7,
            'st_factor1': 2.1,
            'st_length2': 10,
            'st_factor2': 1.0,
            'strategy_mode': 'dual',
            'timeframe': 1,
            'select_by': 'premium',
            'target_option_value': 50
        }
        self.positions = []
        self.last_ltp = 0
        self.logs = []
        self.pnl = 0.0
        self.logged_in = False
        self.token_cache = {}
        self.lock = threading.Lock()

    def add_log(self, message):
        msg = f"{datetime.now().strftime('%H:%M:%S')} - {message}"
        self.logs.append(msg)
        print(msg)
        if len(self.logs) > 100:
            self.logs.pop(0)

    def start(self, user_config):
        with self.lock:
            if self.is_running:
                return
            self.config.update(user_config)

            self.add_log("Attempting Login...")
            res = self.api.login_user(
                self.config['userid'],
                self.config['password'],
                self.config['totp_secret'],
                self.config['api_key'],
                self.config.get('vendor_code', ''),
                self.config.get('imei', '')
            )
            if not res or res.get('stat') != 'Ok':
                self.add_log(f"Login Failed: {res.get('emsg') if res else 'Unknown Error'}")
                self.logged_in = False
                return # Block start even in Paper mode as API access is needed
            else:
                self.add_log("Login Successful")
                self.logged_in = True

            self.is_running = True
            self.add_log(f"Starting Algo in {self.config['trading_mode']} mode")

        self.thread = threading.Thread(target=self.run_loop)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        with self.lock:
            self.is_running = False
            self.add_log("Stopping Algo...")

    def run_loop(self):
        while self.is_running:
            try:
                exch = 'NSE' if self.config['instrument'] == 'NIFTY' else 'BSE'
                symbol = 'Nifty 50' if self.config['instrument'] == 'NIFTY' else 'SENSEX'

                ltp = self.api.get_ltp(exch, symbol)
                if ltp:
                    self.last_ltp = ltp

                    cache_key = f"{exch}:{symbol}"
                    if cache_key not in self.token_cache:
                        token_res = self.api.searchscrip(exch, symbol)
                        if token_res and token_res['stat'] == 'Ok':
                            self.token_cache[cache_key] = token_res['values'][0]['token']

                    token = self.token_cache.get(cache_key)
                    if token:
                        tf = int(self.config.get('timeframe', 1))
                        candles = self.api.get_time_price_series(exch, token, interval=tf)
                        if candles:
                            df = pd.DataFrame(candles)
                            df['high'] = df['inth'].astype(float)
                            df['low'] = df['intl'].astype(float)
                            df['close'] = df['intc'].astype(float)
                            df = df.iloc[::-1]

                            signal = get_strategy_signals(df,
                                                          self.config['st_length1'], self.config['st_factor1'],
                                                          self.config['st_length2'], self.config['st_factor2'],
                                                          strategy_mode=self.config.get('strategy_mode', 'dual'))

                            if signal != 'NONE':
                                self.handle_signal(signal, ltp)

                self.manage_positions()
                time.sleep(1)
            except Exception as e:
                self.add_log(f"Error in engine loop: {str(e)}")
                time.sleep(5)

    def handle_signal(self, signal, index_ltp):
        with self.lock:
            if any(p['status'] == 'OPEN' for p in self.positions):
                return

            self.add_log(f"Signal detected: {signal} at {index_ltp}")

            opt_type = 'CE' if signal == 'BUY_CALL' else 'PE'
            exch_opt = 'NFO' if self.config['instrument'] == 'NIFTY' else 'BFO'
            underlying = 'NIFTY' if self.config['instrument'] == 'NIFTY' else 'SENSEX'

            strike_step = 50 if underlying == 'NIFTY' else 100
            atm_strike = round(index_ltp / strike_step) * strike_step

            # Fetch option chain with Greeks if needed
            fetch_greeks = self.config.get('select_by') == 'delta'
            chain = self.api.get_option_chain_with_quotes(exch_opt, underlying, atm_strike, count=10, fetch_greeks=fetch_greeks)
            filtered_chain = [o for o in chain if o.get('optt') == opt_type]

            selected_opt = find_nearest_option(filtered_chain, self.config['target_option_value'], self.config['select_by'])

            if not selected_opt:
                self.add_log("Could not find suitable option contract")
                return

            entry_price = selected_opt['lp']
            # Fetch lot size from broker dynamically
            lot_size = self.api.get_instrument_lot_size(selected_opt['exch'], selected_opt['tsym'])

            new_pos = {
                'symbol': selected_opt['tsym'],
                'exch': selected_opt['exch'],
                'token': selected_opt['token'],
                'type': opt_type,
                'qty': self.config['lots'] * lot_size,
                'entry_price': entry_price,
                'current_price': entry_price,
                'status': 'OPEN',
                'sl': entry_price * (1 - self.config['max_sl_pct']/100),
                'target': entry_price + self.config['target_points'],
                'pnl': 0.0
            }

            if self.config['trading_mode'] == 'Real':
                self.api.place_order_wrapper('B', self.config['order_type'], new_pos['exch'], new_pos['symbol'], new_pos['qty'], 'MKT')

            self.positions.append(new_pos)
            self.add_log(f"Entered trade: {new_pos['symbol']} at {entry_price}")

    def manage_positions(self):
        with self.lock:
            for p in self.positions:
                if p['status'] == 'OPEN':
                    quote = self.api.get_quotes(p['exch'], p['token'])
                    if quote and quote['stat'] == 'Ok':
                        p['current_price'] = float(quote['lp'])

                    p['pnl'] = (p['current_price'] - p['entry_price']) * p['qty']

                    if p['current_price'] <= p['sl']:
                        self.exit_trade(p, "STOP LOSS")
                    elif self.config['target_type'] == 'ON' and p['current_price'] >= p['target']:
                        self.exit_trade(p, "TARGET")
                    elif self.config['trailing_sl'] == 'ON':
                        tp = self.config.get('trailing_points', 5)
                        new_sl = p['current_price'] - tp
                        if new_sl > p['sl']:
                            p['sl'] = new_sl
                            self.add_log(f"Trailing SL updated to {p['sl']}")

            self.pnl = sum(p['pnl'] for p in self.positions)

    def exit_trade(self, pos, reason):
        pos['status'] = 'CLOSED'
        pos['exit_price'] = pos['current_price']
        self.add_log(f"Exiting trade: {pos['symbol']} due to {reason}")
        if self.config['trading_mode'] == 'Real':
            self.api.place_order_wrapper('S', self.config['order_type'], pos['exch'], pos['symbol'], pos['qty'], 'MKT')

    def get_state(self):
        with self.lock:
            return {
                'running': self.is_running,
                'logged_in': self.logged_in,
                'pnl': self.pnl,
                'positions': self.positions,
                'logs': self.logs[-10:],
                'ltp': self.last_ltp
            }
