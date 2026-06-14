from NorenRestApiPy.NorenApi import NorenApi
import logging
import pyotp
import hashlib
import json
import requests
import urllib.parse
from datetime import datetime

class ShoonyaApiHelper(NorenApi):
    def __init__(self, host='https://api.shoonya.com/NorenWClientAPI/', websocket='wss://api.shoonya.com/NorenWSAPI/'):
        super(ShoonyaApiHelper, self).__init__(host=host, websocket=websocket)

    def login_user(self, userid, password, totp_secret, api_key, vendor_code, imei):
        pwd = hashlib.sha256(password.encode('utf-8')).hexdigest()
        u_appkey = f'{userid}|{api_key}'
        appkey = hashlib.sha256(u_appkey.encode('utf-8')).hexdigest()
        totp = pyotp.TOTP(totp_secret).now()

        # If vendor_code is empty, default to userid + "_U" (Commonly used for Shoonya retail)
        if not vendor_code:
            vendor_code = f"{userid}_U"

        # Use direct REST call to QuickAuth as it is more reliable than SDK's login method
        # and resolves the attribute error by manually setting internal state
        url = "https://api.shoonya.com/NorenWClientAPI/QuickAuth"
        values = {
            "source": "API",
            "apkversion": "1.0.0", # Try standard 1.0.0 first
            "uid": userid,
            "pwd": pwd,
            "factor2": totp,
            "vc": vendor_code,
            "appkey": appkey,
            "imei": imei
        }

        payload = 'jData=' + json.dumps(values)
        try:
            res = requests.post(url, data=payload)
            res_dict = json.loads(res.text)

            if res_dict.get('stat') == 'Ok':
                # Manually set internal SDK session variables to ensure all methods work
                # and to avoid "no attribute" errors
                self._NorenApi__username = userid
                self._NorenApi__accountid = userid
                self._NorenApi__password = password
                self._NorenApi__susertoken = res_dict['susertoken']
                self._NorenApi__access_token = res_dict.get('accesstoken')

                # Also use the SDK's set_session to be thorough
                self.set_session(userid, password, res_dict['susertoken'], res_dict.get('accesstoken'))

            return res_dict
        except Exception as e:
            return {"stat": "Not_Ok", "emsg": str(e)}

    def get_token(self, exchange, symbol):
        search_res = self.searchscrip(exchange=exchange, searchtext=symbol)
        if search_res and search_res['stat'] == 'Ok' and 'values' in search_res:
            for val in search_res['values']:
                if val['tsym'] == symbol or val.get('ts') == symbol:
                    return val['token']
        return None

    def get_ltp(self, exchange, symbol, token=None):
        if not token:
            token = self.get_token(exchange, symbol)

        if token:
            quote = self.get_quotes(exchange=exchange, token=token)
            if quote and quote['stat'] == 'Ok':
                return float(quote['lp'])
        return None

    def get_instrument_lot_size(self, exchange, symbol, token=None):
        if not token:
            token = self.get_token(exchange, symbol)

        if token:
            info = self.get_security_info(exchange=exchange, token=token)
            if info and info['stat'] == 'Ok':
                return int(info['ls'])
        return 1

    def get_option_chain_with_quotes(self, exchange, symbol, strikeprice, count=5, fetch_greeks=False):
        chain = self.get_option_chain(exchange=exchange, tradingsymbol=symbol,
                                       strikeprice=strikeprice, count=count)
        if chain and chain['stat'] == 'Ok' and 'values' in chain:
            for opt in chain['values']:
                quote = self.get_quotes(exchange=opt['exch'], token=opt['token'])
                if quote and quote['stat'] == 'Ok':
                    opt['lp'] = float(quote.get('lp', 0))
                else:
                    opt['lp'] = 0

                opt['delta'] = 0 # Default delta
                if fetch_greeks:
                    try:
                        # Attempt to fetch real Greeks from API
                        # Usually requires spot price, strike, and expiry
                        # We use a simplified fallback if the API call fails or is not available
                        # get_option_greek(expiredate, StrikePrice, SpotPrice, InitRate, Volatility, OptionType)
                        # For this we would need expiry date which is available in security info or chain
                        # For now, keeping the ITM/ATM/OTM approximation but marking it as such
                        # or if we had expiry:
                        # greeks = self.get_option_greek(opt['exd'], opt['strprc'], strikeprice, '10', '20', opt['optt'])

                        strike = float(opt['strprc'])
                        spot = float(strikeprice)
                        is_ce = opt['optt'] == 'CE'

                        if is_ce:
                            if spot > strike: opt['delta'] = 0.7  # ITM
                            elif spot < strike: opt['delta'] = 0.3 # OTM
                            else: opt['delta'] = 0.5 # ATM
                        else:
                            if spot < strike: opt['delta'] = -0.7 # ITM
                            elif spot > strike: opt['delta'] = -0.3 # OTM
                            else: opt['delta'] = -0.5 # ATM
                    except:
                        opt['delta'] = 0.5
            return chain['values']
        return []

    def place_order_wrapper(self, buy_sell, product, exchange, symbol, qty, price_type, price=0, trigger_price=0):
        return self.place_order(buy_or_sell=buy_sell, product_type=product,
                                exchange=exchange, tradingsymbol=symbol,
                                quantity=qty, discloseqty=0,
                                price_type=price_type, price=price, trigger_price=trigger_price)
