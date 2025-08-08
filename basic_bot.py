import streamlit as st
from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceRequestException

# Set up Streamlit page configuration
st.set_page_config(page_title="Binance Testnet Trading Bot", layout="centered")

st.title("Binance Futures Testnet Trading Bot")

# Sidebar for taking API credentials from the user
st.sidebar.header("API Credentials")
api_key = st.sidebar.text_input("API Key")
api_secret = st.sidebar.text_input("API Secret", type="password")

client = None
symbols = []

if api_key and api_secret:
    try:
        # Create Binance Client with testnet flag
        client = Client(api_key, api_secret, testnet=True)
        client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"

        # Time synchronization fix to avoid recvWindow timestamp errors
        try:
            server_time = client.get_server_time()
            client.timestamp_offset = int(server_time['serverTime']) - client._get_local_time()
        except BinanceRequestException as e:
            st.sidebar.error(f"Time sync error: {e}")

        # Fetch available futures symbols for selection dropdown
        info = client.futures_exchange_info()
        symbols = [s["symbol"] for s in info["symbols"]]
        st.sidebar.success("API Connected and symbols loaded!")
    except Exception as e:
        st.sidebar.error(f"API Connection Error: {e}")

if symbols:
    st.subheader("Place an Order")

    with st.form("order_form"):
        symbol = st.selectbox("Trading Symbol", symbols)
        order_type = st.selectbox("Order Type", ["MARKET", "LIMIT", "STOP"])
        side = st.selectbox("Side", ["BUY", "SELL"])
        quantity = st.number_input("Quantity", min_value=0.0001, format="%.8f", value=0.01)
        price = st.number_input("Limit Price (for LIMIT/STOP orders)", min_value=0.0, format="%.8f", value=0.0)
        stop_price = st.number_input("Stop Price (for STOP orders)", min_value=0.0, format="%.8f", value=0.0)
        submitted = st.form_submit_button("Place Order")

    if submitted:
        # Prepare order parameters dictionary
        params = {
            "symbol": symbol,
            "side": SIDE_BUY if side == "BUY" else SIDE_SELL,
            "quantity": quantity,
            "type": None,
            "recvWindow": 5000  # 5 seconds window to tolerate network delay
        }

        # Assign order type and additional parameters as needed
        if order_type == "MARKET":
            params["type"] = ORDER_TYPE_MARKET
        elif order_type == "LIMIT":
            if price <= 0:
                st.error("Please enter a valid limit price > 0")
            else:
                params.update(type=ORDER_TYPE_LIMIT, price=price, timeInForce=TIME_IN_FORCE_GTC)
        elif order_type == "STOP":
            if price <= 0 or stop_price <= 0:
                st.error("Please enter valid limit and stop prices > 0")
            else:
                params.update(type=ORDER_TYPE_STOP, price=price, stopPrice=stop_price, timeInForce=TIME_IN_FORCE_GTC)
        else:
            st.error("Unknown order type selected!")

        # Place order if parameters are valid
        if params["type"]:
            try:
                order = client.futures_create_order(**params)
                st.success("Order placed successfully!")

                # Show order details in a table format
                st.table({
                    "Order ID": [order.get("orderId", "")],
                    "Symbol": [order.get("symbol", "")],
                    "Side": [order.get("side", "")],
                    "Type": [order.get("type", "")],
                    "Status": [order.get("status", "")],
                    "Price": [order.get("price", "")],
                    "Original Quantity": [order.get("origQty", "")],
                    "Executed Quantity": [order.get("executedQty", "")]
                })

            except Exception as e:
                st.error(f"Order failed: {e}")
else:
    st.info("Please enter your Binance Futures Testnet API credentials on the sidebar to start.")

# Footer note
st.markdown(
    """
    ---
    **Note:**  
    This bot interacts with Binance Futures Testnet — safe for simulated trades only.  
    Ensure your system clock is synchronized to avoid timestamp errors.
    """
)
