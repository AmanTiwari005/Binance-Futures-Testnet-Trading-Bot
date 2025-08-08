import streamlit as st
from binance.client import Client
from binance.enums import *

# Set up Streamlit page
st.set_page_config(page_title="Binance Testnet Trading Bot", layout="centered")

st.title("Binance Futures Testnet Trading Bot")

# Sidebar for credentials
st.sidebar.header("API Credentials")
api_key = st.sidebar.text_input("API Key")
api_secret = st.sidebar.text_input("API Secret", type="password")

# Connect and fetch symbols
client = None
symbols = []
if api_key and api_secret:
    try:
        client = Client(api_key, api_secret, testnet=True)
        client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"
        info = client.futures_exchange_info()
        symbols = [s["symbol"] for s in info["symbols"]]
        st.sidebar.success("API Connected!")
    except Exception as e:
        st.sidebar.error(f"API Error: {e}")

# Order entry form (disable unless connected)
if symbols:
    st.subheader("Place an Order")
    with st.form("order_form"):
        symbol = st.selectbox("Trading Symbol", symbols)
        order_type = st.selectbox("Order Type", ["MARKET", "LIMIT", "STOP"])
        side = st.selectbox("Side", ["BUY", "SELL"])
        quantity = st.number_input("Quantity", min_value=0.0001, value=0.01)
        price = st.number_input("Limit Price (for LIMIT/STOP)", min_value=0.0, value=0.0)
        stop_price = st.number_input("Stop Price (for STOP orders)", min_value=0.0, value=0.0)
        submitted = st.form_submit_button("Place Order")

    if submitted:
        params = {
            "symbol": symbol,
            "side": SIDE_BUY if side == "BUY" else SIDE_SELL,
            "quantity": quantity,
            "type": None
        }
        if order_type == "MARKET":
            params["type"] = ORDER_TYPE_MARKET
        elif order_type == "LIMIT":
            params.update(type=ORDER_TYPE_LIMIT, price=price, timeInForce=TIME_IN_FORCE_GTC)
        elif order_type == "STOP":
            params.update(type=ORDER_TYPE_STOP, price=price, stopPrice=stop_price, timeInForce=TIME_IN_FORCE_GTC)

        # Place order and report results
        try:
            order = client.futures_create_order(**params)
            st.success("Order placed successfully!")
            st.table({k: [str(order.get(k, ""))] for k in ["orderId", "symbol", "side", "type", "status", "price", "origQty", "executedQty"]})
        except Exception as e:
            st.error(f"Order failed: {e}")
else:
    st.info("Connect your API key & secret to begin.")


