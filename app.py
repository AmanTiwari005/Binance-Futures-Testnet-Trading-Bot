import streamlit as st
import time
import datetime
import logging
from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceRequestException, BinanceAPIException

# --- Logging setup ---
logging.basicConfig(
    filename="trading_bot.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# --- Streamlit app configuration ---
st.set_page_config(page_title="Binance Testnet Trading Bot", layout="centered")
st.title("Enhanced Binance Futures Testnet Trading Bot")

# --- Sidebar: API credentials input ---
st.sidebar.header("API Credentials")
api_key = st.sidebar.text_input("API Key")
api_secret = st.sidebar.text_input("API Secret", type="password")

client = None
symbols = []
account_info = {}

# Initialize in-session order history
if 'order_history' not in st.session_state:
    st.session_state.order_history = []

# --- Connect to Binance Futures Testnet API and fetch symbols/account info ---
if api_key and api_secret:
    try:
        client = Client(api_key, api_secret, testnet=True)
        client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"

        # Synchronize time offset to fix timestamp errors
        server_time = client.get_server_time()
        local_time = int(time.time() * 1000)  # current epoch in ms
        client.timestamp_offset = server_time['serverTime'] - local_time
        logging.info("Time synchronized with Binance server.")

        # Load trading symbols
        info = client.futures_exchange_info()
        symbols = [s["symbol"] for s in info["symbols"]]
        logging.info(f"Fetched {len(symbols)} symbols.")

        # Load USDT balance for display
        try:
            balances = client.futures_account_balance()
            usdt_item = next((b for b in balances if b["asset"] == "USDT"), None)
            account_info['USDT_balance'] = usdt_item['balance'] if usdt_item else "N/A"
        except Exception as e:
            account_info['USDT_balance'] = "N/A"
            logging.error(f"Error fetching USDT balance: {e}")

        st.sidebar.success("API connected and symbols loaded!")

    except Exception as e:
        st.sidebar.error(f"API Connection Error: {e}")
        logging.error(f"API connection failed: {e}")

# --- Main interface ---
if symbols:
    col1, col2 = st.columns([3, 1])
    with col1:
        symbol = st.selectbox("Select Trading Symbol", symbols)

        # Show live price
        current_price = None
        try:
            ticker = client.futures_symbol_ticker(symbol=symbol)
            current_price = float(ticker["price"])
            st.markdown(f"### Current Price: $ {current_price:.8f}")
        except Exception as e:
            st.markdown("### Current Price: -")
            logging.error(f"Error fetching price for {symbol}: {e}")

        # Order form
        with st.form("order_form"):
            order_type = st.selectbox("Order Type", ["MARKET", "LIMIT", "STOP"])
            side = st.selectbox("Side", ["BUY", "SELL"])
            quantity = st.number_input("Quantity", min_value=0.0001, format="%.8f", value=0.01)
            price = None
            stop_price = None

            if order_type in ("LIMIT", "STOP"):
                price = st.number_input("Limit Price", min_value=0.0, format="%.8f", value=0.0)
            if order_type == "STOP":
                stop_price = st.number_input("Stop Price", min_value=0.0, format="%.8f", value=0.0)

            submitted = st.form_submit_button("Place Order")

        if submitted:
            # Validate and prepare parameters
            params = {
                "symbol": symbol,
                "side": SIDE_BUY if side == "BUY" else SIDE_SELL,
                "quantity": quantity,
                "type": None,
                "recvWindow": 5000
            }

            errors = []
            if order_type == "MARKET":
                params["type"] = ORDER_TYPE_MARKET
            elif order_type == "LIMIT":
                if not price or price <= 0:
                    errors.append("Limit price must be greater than zero.")
                else:
                    params.update(type=ORDER_TYPE_LIMIT, price=price, timeInForce=TIME_IN_FORCE_GTC)
            elif order_type == "STOP":
                if not price or price <= 0:
                    errors.append("Limit price must be greater than zero.")
                if not stop_price or stop_price <= 0:
                    errors.append("Stop price must be greater than zero.")
                if not errors:
                    params.update(type=ORDER_TYPE_STOP, price=price, stopPrice=stop_price, timeInForce=TIME_IN_FORCE_GTC)
            else:
                errors.append("Unsupported order type.")

            # Report errors if any
            if errors:
                for err in errors:
                    st.error(err)
                    logging.warning(f"Input validation error: {err}")
            else:
                try:
                    logging.info(f"Placing order with params: {params}")
                    order = client.futures_create_order(**params)
                    st.success(f"Order placed successfully! Order ID: {order.get('orderId')}")
                    logging.info(f"Order response: {order}")

                    # Show order details in table
                    st.table({
                        "Field": ["Order ID", "Symbol", "Side", "Type", "Status", "Price", "Original Quantity", "Executed Quantity"],
                        "Value": [order.get(k, "") for k in ["orderId", "symbol", "side", "type", "status", "price", "origQty", "executedQty"]]
                    })

                    # Append order to session history
                    st.session_state.order_history.append({
                        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "symbol": order.get("symbol"),
                        "side": order.get("side"),
                        "type": order.get("type"),
                        "status": order.get("status"),
                        "price": order.get("price"),
                        "quantity": order.get("origQty"),
                    })

                except BinanceAPIException as e:
                    st.error(f"Order failed: {e.message}")
                    logging.error(f"Order API error: {e.message}")
                except Exception as e:
                    st.error(f"Order failed: {e}")
                    logging.error(f"Order unexpected error: {e}")

    with col2:
        usdt_balance = account_info.get('USDT_balance', "N/A")
        st.markdown(f"### USDT Balance: {usdt_balance}")

    # Show session order history
    if st.session_state.order_history:
        st.markdown("---")
        st.subheader("Order History (Session)")
        for ord in reversed(st.session_state.order_history):
            side_color = "🟢 BUY" if ord["side"] == "BUY" else "🔴 SELL"
            st.markdown(f"**[{ord['time']}] {ord['symbol']}** - {side_color} | "
                        f"Type: {ord['type']} | Status: {ord['status']} | "
                        f"Price: {ord['price']} | Qty: {ord['quantity']}")

else:
    st.info("Please enter your Binance Futures Testnet API credentials on the sidebar to connect.")

# Footer note
st.markdown(
    """
    ---
    **Note:**  
    This bot interacts with Binance Futures Testnet — safe for testing only.  
    Make sure your system time is synchronized to prevent timestamp errors.  
    Use responsibly and at your own risk.
    """
)
