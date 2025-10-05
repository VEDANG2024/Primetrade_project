"""
Binance Futures Testnet Trading Bot
Supports Market, Limit, Stop-Limit, and OCO orders
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BasicBot:
    """
    A trading bot for Binance Futures Testnet with support for multiple order types.
    """
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        """
        Initialize the trading bot with API credentials.
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Use testnet (default: True)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        try:
            self.client = Client(api_key, api_secret, testnet=testnet)
            
            if testnet:
                # Set testnet URL for futures
                self.client.API_URL = 'https://testnet.binancefuture.com'
                logger.info("Connected to Binance Futures Testnet")
            else:
                logger.info("Connected to Binance Futures Live")
                
            # Test connection
            self._test_connection()
            
        except Exception as e:
            logger.error(f"Failed to initialize client: {str(e)}")
            raise
    
    def _test_connection(self) -> bool:
        """Test API connection and permissions."""
        try:
            self.client.futures_ping()
            account = self.client.futures_account()
            logger.info(f"Connection successful. Account balance: {account['totalWalletBalance']} USDT")
            return True
        except BinanceAPIException as e:
            logger.error(f"API Error: {e.status_code} - {e.message}")
            return False
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def _validate_symbol(self, symbol: str) -> bool:
        """Validate if symbol exists on Binance Futures."""
        try:
            exchange_info = self.client.futures_exchange_info()
            valid_symbols = [s['symbol'] for s in exchange_info['symbols']]
            return symbol.upper() in valid_symbols
        except Exception as e:
            logger.error(f"Symbol validation failed: {str(e)}")
            return False
    
    def _log_request(self, order_type: str, params: Dict[str, Any]):
        """Log API request details."""
        logger.info(f"Placing {order_type} order with params: {json.dumps(params, indent=2)}")
    
    def _log_response(self, response: Dict[str, Any]):
        """Log API response details."""
        logger.info(f"Order response: {json.dumps(response, indent=2)}")
    
    def get_account_balance(self) -> Dict[str, Any]:
        """Get account balance information."""
        try:
            account = self.client.futures_account()
            balance = {
                'totalWalletBalance': account['totalWalletBalance'],
                'availableBalance': account['availableBalance'],
                'assets': []
            }
            
            for asset in account['assets']:
                if float(asset['walletBalance']) > 0:
                    balance['assets'].append({
                        'asset': asset['asset'],
                        'walletBalance': asset['walletBalance'],
                        'availableBalance': asset['availableBalance']
                    })
            
            logger.info(f"Account balance retrieved: {balance['totalWalletBalance']} USDT")
            return balance
        except Exception as e:
            logger.error(f"Failed to get account balance: {str(e)}")
            raise
    
    def place_market_order(self, symbol: str, side: str, quantity: float) -> Dict[str, Any]:
        """
        Place a market order.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            
        Returns:
            Order response dictionary
        """
        symbol = symbol.upper()
        side = side.upper()
        
        if not self._validate_symbol(symbol):
            raise ValueError(f"Invalid symbol: {symbol}")
        
        if side not in ['BUY', 'SELL']:
            raise ValueError("Side must be 'BUY' or 'SELL'")
        
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': quantity
        }
        
        self._log_request('MARKET', params)
        
        try:
            response = self.client.futures_create_order(**params)
            self._log_response(response)
            logger.info(f"✓ Market order executed: {side} {quantity} {symbol}")
            return response
        except BinanceAPIException as e:
            logger.error(f"API Error: {e.status_code} - {e.message}")
            raise
        except Exception as e:
            logger.error(f"Order placement failed: {str(e)}")
            raise
    
    def place_limit_order(self, symbol: str, side: str, quantity: float, 
                         price: float, time_in_force: str = 'GTC') -> Dict[str, Any]:
        """
        Place a limit order.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            price: Limit price
            time_in_force: 'GTC', 'IOC', or 'FOK' (default: 'GTC')
            
        Returns:
            Order response dictionary
        """
        symbol = symbol.upper()
        side = side.upper()
        
        if not self._validate_symbol(symbol):
            raise ValueError(f"Invalid symbol: {symbol}")
        
        if side not in ['BUY', 'SELL']:
            raise ValueError("Side must be 'BUY' or 'SELL'")
        
        if quantity <= 0 or price <= 0:
            raise ValueError("Quantity and price must be positive")
        
        if time_in_force not in ['GTC', 'IOC', 'FOK']:
            raise ValueError("time_in_force must be 'GTC', 'IOC', or 'FOK'")
        
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'LIMIT',
            'quantity': quantity,
            'price': price,
            'timeInForce': time_in_force
        }
        
        self._log_request('LIMIT', params)
        
        try:
            response = self.client.futures_create_order(**params)
            self._log_response(response)
            logger.info(f"✓ Limit order placed: {side} {quantity} {symbol} @ {price}")
            return response
        except BinanceAPIException as e:
            logger.error(f"API Error: {e.status_code} - {e.message}")
            raise
        except Exception as e:
            logger.error(f"Order placement failed: {str(e)}")
            raise
    
    def place_stop_limit_order(self, symbol: str, side: str, quantity: float,
                              stop_price: float, limit_price: float,
                              time_in_force: str = 'GTC') -> Dict[str, Any]:
        """
        Place a stop-limit order.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            stop_price: Stop trigger price
            limit_price: Limit price after stop is triggered
            time_in_force: 'GTC', 'IOC', or 'FOK' (default: 'GTC')
            
        Returns:
            Order response dictionary
        """
        symbol = symbol.upper()
        side = side.upper()
        
        if not self._validate_symbol(symbol):
            raise ValueError(f"Invalid symbol: {symbol}")
        
        if side not in ['BUY', 'SELL']:
            raise ValueError("Side must be 'BUY' or 'SELL'")
        
        if quantity <= 0 or stop_price <= 0 or limit_price <= 0:
            raise ValueError("Quantity, stop_price, and limit_price must be positive")
        
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'STOP',
            'quantity': quantity,
            'price': limit_price,
            'stopPrice': stop_price,
            'timeInForce': time_in_force
        }
        
        self._log_request('STOP_LIMIT', params)
        
        try:
            response = self.client.futures_create_order(**params)
            self._log_response(response)
            logger.info(f"✓ Stop-limit order placed: {side} {quantity} {symbol} @ stop:{stop_price} limit:{limit_price}")
            return response
        except BinanceAPIException as e:
            logger.error(f"API Error: {e.status_code} - {e.message}")
            raise
        except Exception as e:
            logger.error(f"Order placement failed: {str(e)}")
            raise
    
    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """Get all open orders or open orders for a specific symbol."""
        try:
            if symbol:
                orders = self.client.futures_get_open_orders(symbol=symbol.upper())
            else:
                orders = self.client.futures_get_open_orders()
            
            logger.info(f"Retrieved {len(orders)} open orders")
            return orders
        except Exception as e:
            logger.error(f"Failed to get open orders: {str(e)}")
            raise
    
    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an open order."""
        try:
            response = self.client.futures_cancel_order(
                symbol=symbol.upper(),
                orderId=order_id
            )
            logger.info(f"✓ Order {order_id} cancelled for {symbol}")
            return response
        except Exception as e:
            logger.error(f"Failed to cancel order: {str(e)}")
            raise
    
    def get_order_status(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Get status of a specific order."""
        try:
            order = self.client.futures_get_order(
                symbol=symbol.upper(),
                orderId=order_id
            )
            logger.info(f"Order status: {order['status']}")
            return order
        except Exception as e:
            logger.error(f"Failed to get order status: {str(e)}")
            raise
    
    def get_current_price(self, symbol: str) -> float:
        """Get current market price for a symbol."""
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol.upper())
            price = float(ticker['price'])
            logger.info(f"{symbol} current price: {price}")
            return price
        except Exception as e:
            logger.error(f"Failed to get price: {str(e)}")
            raise


def display_menu():
    """Display the CLI menu."""
    print("\n" + "="*60)
    print("  BINANCE FUTURES TESTNET TRADING BOT")
    print("="*60)
    print("\n[1] View Account Balance")
    print("[2] Place Market Order")
    print("[3] Place Limit Order")
    print("[4] Place Stop-Limit Order")
    print("[5] View Open Orders")
    print("[6] Cancel Order")
    print("[7] Get Order Status")
    print("[8] Get Current Price")
    print("[9] Exit")
    print("\n" + "="*60)


def get_float_input(prompt: str) -> float:
    """Get and validate float input."""
    while True:
        try:
            value = float(input(prompt))
            if value <= 0:
                print("❌ Value must be positive. Try again.")
                continue
            return value
        except ValueError:
            print("❌ Invalid input. Please enter a number.")


def get_choice_input(prompt: str, valid_choices: list) -> str:
    """Get and validate choice input."""
    while True:
        choice = input(prompt).upper()
        if choice in valid_choices:
            return choice
        print(f"❌ Invalid choice. Please choose from: {', '.join(valid_choices)}")


def main():
    """Main CLI application."""
    print("\n🚀 Starting Binance Futures Testnet Trading Bot...")
    
    # Get API credentials
    api_key = os.environ.get('BINANCE_TESTNET_API_KEY')
    api_secret = os.environ.get('BINANCE_TESTNET_API_SECRET')
    
    if not api_key or not api_secret:
        print("\n⚠️  API credentials not found in environment variables.")
        print("Please set BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_API_SECRET")
        api_key = input("\nEnter your Binance Testnet API Key: ").strip()
        api_secret = input("Enter your Binance Testnet API Secret: ").strip()
    
    try:
        bot = BasicBot(api_key, api_secret, testnet=True)
        print("\n✅ Bot initialized successfully!")
        
        while True:
            display_menu()
            choice = input("\nSelect an option (1-9): ").strip()
            
            try:
                if choice == '1':
                    # View Account Balance
                    balance = bot.get_account_balance()
                    print(f"\n💰 Total Balance: {balance['totalWalletBalance']} USDT")
                    print(f"Available Balance: {balance['availableBalance']} USDT")
                    if balance['assets']:
                        print("\nAssets:")
                        for asset in balance['assets']:
                            print(f"  {asset['asset']}: {asset['walletBalance']} (Available: {asset['availableBalance']})")
                
                elif choice == '2':
                    # Place Market Order
                    symbol = input("\nEnter symbol (e.g., BTCUSDT): ").strip().upper()
                    side = get_choice_input("Enter side (BUY/SELL): ", ['BUY', 'SELL'])
                    quantity = get_float_input("Enter quantity: ")
                    
                    confirm = input(f"\n⚠️  Confirm {side} {quantity} {symbol} at MARKET price? (yes/no): ")
                    if confirm.lower() == 'yes':
                        response = bot.place_market_order(symbol, side, quantity)
                        print(f"\n✅ Order executed! Order ID: {response['orderId']}")
                        print(f"Status: {response['status']}")
                
                elif choice == '3':
                    # Place Limit Order
                    symbol = input("\nEnter symbol (e.g., BTCUSDT): ").strip().upper()
                    side = get_choice_input("Enter side (BUY/SELL): ", ['BUY', 'SELL'])
                    quantity = get_float_input("Enter quantity: ")
                    price = get_float_input("Enter limit price: ")
                    
                    confirm = input(f"\n⚠️  Confirm {side} {quantity} {symbol} @ {price}? (yes/no): ")
                    if confirm.lower() == 'yes':
                        response = bot.place_limit_order(symbol, side, quantity, price)
                        print(f"\n✅ Order placed! Order ID: {response['orderId']}")
                        print(f"Status: {response['status']}")
                
                elif choice == '4':
                    # Place Stop-Limit Order
                    symbol = input("\nEnter symbol (e.g., BTCUSDT): ").strip().upper()
                    side = get_choice_input("Enter side (BUY/SELL): ", ['BUY', 'SELL'])
                    quantity = get_float_input("Enter quantity: ")
                    stop_price = get_float_input("Enter stop price: ")
                    limit_price = get_float_input("Enter limit price: ")
                    
                    confirm = input(f"\n⚠️  Confirm {side} {quantity} {symbol} stop:{stop_price} limit:{limit_price}? (yes/no): ")
                    if confirm.lower() == 'yes':
                        response = bot.place_stop_limit_order(symbol, side, quantity, stop_price, limit_price)
                        print(f"\n✅ Order placed! Order ID: {response['orderId']}")
                        print(f"Status: {response['status']}")
                
                elif choice == '5':
                    # View Open Orders
                    symbol = input("\nEnter symbol (or press Enter for all): ").strip().upper()
                    orders = bot.get_open_orders(symbol if symbol else None)
                    
                    if orders:
                        print(f"\n📋 Open Orders ({len(orders)}):")
                        for order in orders:
                            print(f"\n  Order ID: {order['orderId']}")
                            print(f"  Symbol: {order['symbol']}")
                            print(f"  Type: {order['type']}")
                            print(f"  Side: {order['side']}")
                            print(f"  Price: {order['price']}")
                            print(f"  Quantity: {order['origQty']}")
                            print(f"  Status: {order['status']}")
                    else:
                        print("\n✓ No open orders")
                
                elif choice == '6':
                    # Cancel Order
                    symbol = input("\nEnter symbol: ").strip().upper()
                    order_id = int(input("Enter order ID: "))
                    
                    response = bot.cancel_order(symbol, order_id)
                    print(f"\n✅ Order {order_id} cancelled successfully!")
                
                elif choice == '7':
                    # Get Order Status
                    symbol = input("\nEnter symbol: ").strip().upper()
                    order_id = int(input("Enter order ID: "))
                    
                    order = bot.get_order_status(symbol, order_id)
                    print(f"\n📊 Order Status:")
                    print(f"  Order ID: {order['orderId']}")
                    print(f"  Symbol: {order['symbol']}")
                    print(f"  Status: {order['status']}")
                    print(f"  Type: {order['type']}")
                    print(f"  Side: {order['side']}")
                    print(f"  Price: {order['price']}")
                    print(f"  Quantity: {order['origQty']}")
                    print(f"  Executed: {order['executedQty']}")
                
                elif choice == '8':
                    # Get Current Price
                    symbol = input("\nEnter symbol: ").strip().upper()
                    price = bot.get_current_price(symbol)
                    print(f"\n💵 {symbol} current price: {price} USDT")
                
                elif choice == '9':
                    print("\n👋 Exiting bot. Goodbye!")
                    break
                
                else:
                    print("\n❌ Invalid option. Please select 1-9.")
            
            except ValueError as e:
                print(f"\n❌ Validation Error: {str(e)}")
            except BinanceAPIException as e:
                print(f"\n❌ Binance API Error: {e.message}")
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
            
            input("\nPress Enter to continue...")
    
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        print(f"\n❌ Fatal Error: {str(e)}")
        print("Please check your API credentials and try again.")


if __name__ == "__main__":
    main()
