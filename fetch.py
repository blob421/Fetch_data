import sqlite3
import json
from datetime import datetime, timezone, timedelta
import asyncio
import aiohttp
import time
import os

path = os.path.join(os.path.dirname(__file__), 'ApiKey.txt')
with open(path, 'r') as file:
   headers = json.load(file)

url_btc = "https://openapiv1.coinstats.app/coins?currency=USD&name=bitcoin&symbol=BTC"
url_eth = "https://openapiv1.coinstats.app/coins?currency=USD&name=ethereum&symbol=ETH"



async def fetch_data_with_retry(url: str, headers: dict, max_retries: int = 5, wait_time: int = 10) -> dict:
    """
    Asynchronously fetch data from a given API endpoint with a retry mechanism.

    This function attempts to retrieve JSON data from the specified `url` using 
    an asynchronous HTTP request. If the request fails due to client errors, it 
    retries up to `max_retries` times, waiting `wait_time` seconds between attempts.

    Args:
        - url (str): The API endpoint to request data from.
        - headers (dict): A dictionary containing HTTP headers for the request.
        - max_retries (int, optional): The number of retry attempts in case of failure. Defaults to 5.
        - wait_time (int, optional): The time (in seconds) to wait between retries. Defaults to 10.

    Returns:
        - dict or None: The parsed JSON response as a dictionary if successful, otherwise `None`.

    Raises:
        - aiohttp.ClientError: If an issue occurs during the request.
    
    Example:
        >>> response = await fetch_data_with_retry("https://api.example.com/data", headers={"Authorization": "Bearer token"})
        >>> print(response)
        {'price': 42000, 'volume': 345678}
    """
    for attempt in range(max_retries):
     
     try:
        async with aiohttp.ClientSession() as session:
           async with session.get(url, headers=headers) as response:
             response.raise_for_status()
             return await response.json()
    
     except aiohttp.ClientError as e:
        print(f'Attempt{attempt + 1} failed: {e}')
        await asyncio.sleep(wait_time)
   
    print("Max retries reached. Failed to fetch data.")
    return None 



async def fetch_sentiment():
 """
 Fetch sentiment data from the Fear & Greed Index API.

 This function retrieves sentiment data from Alternative.me's Fear & Greed Index API
 and stores the fetched value and classification in global variables (`fng_name`, `fng_value`).
 If the request fails, it prints an error message and defaults the values to `None`.

 The function uses `fetch_data_with_retry()` to handle retries in case of failures.

 Global Variables:
    - fng_name (str or None): Sentiment classification (e.g., "Greed", "Fear").
    - fng_value (int or None): Sentiment score ranging from 0 to 100.

 Raises:
    - json.JSONDecodeError: If the response JSON parsing fails.
    - IndexError, KeyError: If expected fields are missing in the response data.
    - Exception: For any other unexpected errors.

 Example:
    >>> await fetch_sentiment()
    >>> print(fng_name, fng_value)
    "Greed", 74
 """
 global fng_name, fng_value
 date_time = datetime.now(timezone.utc) 
 fng_name, fng_value = None, None

 url2 = 'https://api.alternative.me/fng/?limit=2&format=json'

 try:
      
      response2 = await fetch_data_with_retry(url2, None)

      if response2 and "data" in response2 and response2["data"]:
         fng_value = response2['data'][0]['value']
         fng_name = response2['data'][0]['value_classification']
         return
     
      if response2 is None:         
         print(f"{date_time} Couldn't get sentiment data, returning 'None' ")
         return
       
   
 except json.JSONDecodeError as e:
       print(f"{date_time} Couldn't get sentiment data, returning 'None' : {e}")
       return

 except (IndexError, KeyError) as e:
       print(f"{date_time} Couldn't get sentiment data, returning 'None' : {e}")
       return
            
 except Exception as e:
       print(f"{date_time} Couldn't get sentiment data, returning 'None' : {e}")
       return



async def fetch_marketdata():
    """
    Fetch market-related data from CoinStats and store it in an SQLite3 database.

    This function retrieves cryptocurrency market metrics—including market capitalization,
    trading volume, and Bitcoin dominance—from the CoinStats API. The collected data is stored
    in an SQLite3 database using WAL mode for efficiency. Additionally, sentiment data from
    the Fear & Greed Index is included in the database.

    Global Variables:
        - fng_name (str or None): Sentiment classification (e.g., "Extreme Fear", "Greed").
        - fng_value (int or None): Sentiment score ranging from 0 to 100.

    Database Schema:
        - date (DATETIME): Timestamp of the recorded data.
        - marketCap (INTEGER): Total market capitalization of cryptocurrencies.
        - volume (INTEGER): Overall trading volume.
        - btcDominance (DECIMAL(20,2)): Percentage dominance of Bitcoin in the market.
        - marketCapChange (DECIMAL(20,2)): Change in market capitalization since the last measurement.
        - volumeChange (DECIMAL(20,2)): Change in trading volume over time.
        - btcDominanceChange (DECIMAL(20,2)): Change in Bitcoin's dominance percentage.
        - fear_greed_value (INTEGER): Fear & Greed Index score.
        - fear_greed_name (VARCHAR(20)): Sentiment classification label.

    Error Handling:
        - Handles JSON decoding errors, index/key errors, and generic exceptions.
        - Fails gracefully by printing an error message and storing `None` values when data retrieval fails.
        - Includes a database transaction with WAL mode to optimize performance.

    Raises:
        - json.JSONDecodeError: If the response data cannot be parsed correctly.
        - IndexError, KeyError: If expected fields are missing in the response.
        - sqlite3.Error: If an issue occurs during database insertion.

    Example:
        >>> await fetch_marketdata()
        >>> # Data is stored in the `crypto_data.sqlite` database.
    """
    global fng_name, fng_value
 
    marketCap = None
    volume = None
    btcDominance = None
    marketCapChange = None
    volumeChange = None
    btcDominanceChange = None

    url = "https://openapiv1.coinstats.app/markets"
    date_time = datetime.now(timezone.utc) 

    try:
    
       response = await fetch_data_with_retry(url, headers)
          
       if response is None:
          print(f"{date_time} 'None' values registered (market)")
          pass
   
    
       with sqlite3.connect('crypto_data.sqlite') as conn:
           cursor = conn.cursor() 
        
           conn.execute("PRAGMA journal_mode=WAL;")
           cursor.execute('''CREATE TABLE IF NOT EXISTS market_data 
                           (date DATETIME,
                           marketCap INTEGER, 
                           volume INTEGER, 
                           btcDominance DECIMAL(20, 2),
                           marketCapChange DECIMAL(20, 2),
                           volumeChange DECIMAL(20, 2),
                           btcDominanceChange DECIMAL(20, 2),
                           fear_greed_value INTEGER,
                           fear_greed_name VARCHAR(20))''')
            
           cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_data_date ON market_data(date);')
       
           data = response
            
           marketCap = data.get("marketCap") if data else None
           volume = data.get("volume") if data else None
           btcDominance = data.get("btcDominance") if data else None
           marketCapChange = data.get("marketCapChange") if data else None    
           volumeChange = data.get("volumeChange") if data else None
           btcDominanceChange = data.get("btcDominanceChange") if data else None
           date = date_time
 
    except json.JSONDecodeError as e:
       print(f"{date_time} 'None' values registered (market): {e}")
       pass
    except (IndexError, KeyError) as e:
       print(f"{date_time} 'None' values registered (market): {e}")
       pass
    except Exception as e:
       print(f"{date_time} 'None' values registered (market): {e}")
       pass
        
      
    try:
      cursor.executemany('''INSERT INTO market_data (date, marketCap, volume, btcDominance,
      marketCapChange, volumeChange, btcDominanceChange, fear_greed_value , fear_greed_name)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', [(date, marketCap, volume,
      btcDominance, marketCapChange, volumeChange , btcDominanceChange, fng_value, fng_name)])
        
      conn.commit()
   
       
    except sqlite3.Error as e:
           print(f'Database insert error: {e}')
 
    finally:
      cursor.close()
 


async def fetch_coindata(url: str, coin: str, table_name: str):
 """
    Fetch cryptocurrency market data from an API and store it in an SQLite3 database.

    This function retrieves real-time data for a specific cryptocurrency, including 
    price, volume, supply, market capitalization, and price changes over time. The 
    retrieved information is stored in an SQLite3 database under a dynamically named 
    table.

    Args:
        - url (str): The API endpoint to fetch cryptocurrency data.
        - coin (str): The name of the cryptocurrency being retrieved.
        - table_name (str): The database table where the data will be stored.

    Database Schema:
        - date (DATETIME): Timestamp of the recorded data.
        - price (DECIMAL(20,2)): Current price of the cryptocurrency.
        - volume (DECIMAL(20,2)): Trading volume in the last 24 hours.
        - marketCap (DECIMAL(20,2)): Total market capitalization.
        - availableSupply (DECIMAL(20,2)): Available circulating supply.
        - totalSupply (INTEGER): Total supply of the cryptocurrency.
        - fullyDilutedValuation (DECIMAL(20,2)): Market value if fully diluted.
        - priceChange1h (DECIMAL(20,2)): Price change percentage over 1 hour.
        - priceChange1d (DECIMAL(20,2)): Price change percentage over 24 hours.
        - priceChange1w (DECIMAL(20,2)): Price change percentage over 7 days.

    Error Handling:
        - Handles JSON decoding errors, index/key errors, and general exceptions.
        - Fails gracefully by printing an error message and storing `None` values 
          when data retrieval fails.
        - Uses WAL (Write-Ahead Logging) mode for optimized database transactions.

    Raises:
        - json.JSONDecodeError: If the response data cannot be parsed correctly.
        - IndexError, KeyError: If expected fields are missing in the response.
        - sqlite3.Error: If an issue occurs during database insertion.

    Example:
        >>> await fetch_coindata("https://api.example.com/btc", "Bitcoin", "bitcoin_data")
        >>> # Data is stored in the `crypto_data.sqlite` database.
 """ 
 price = None
 volume = None
 marketCap = None
 availableSupply = None
 totalSupply = None
 fullyDilutedValuation = None
 priceChange1h = None
 priceChange1d = None
 priceChange1w = None

 date_time = datetime.now(timezone.utc) 

 try:
   
   response = await fetch_data_with_retry(url, headers)
   
   if response is None:
      print(f"{date_time} 'None' values registered {coin}")
      pass
   

   with sqlite3.connect('crypto_data.sqlite') as conn:
    
      cursor = conn.cursor()
      conn.execute("PRAGMA journal_mode=WAL;")
      
      cursor.execute(f'''CREATE TABLE IF NOT EXISTS {table_name}
                      (date DATETIME,
                      price DECIMAL(20, 2),
                      volume DECIMAL(20, 2),
                      marketCap DECIMAL(20, 2),
                      availableSupply DECIMAL(20, 2),
                      totalSupply INTEGER,
                      fullyDilutedValuation DECIMAL(20, 2),
                      priceChange1h DECIMAL(20, 2),
                      priceChange1d DECIMAL(20, 2),
                      priceChange1w DECIMAL(20, 2))''')
 
      cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_date ON {table_name}(date);')
    
      price = response["result"][0]["price"] if response else None
      volume = response["result"][0]["volume"] if response else None
      marketCap = response["result"][0]["marketCap"] if response else None
      availableSupply = response["result"][0]["availableSupply"] if response else None
      totalSupply = response["result"][0]["totalSupply"] if response else None
      fullyDilutedValuation = response["result"][0]["fullyDilutedValuation"] if response else None
      priceChange1h = response["result"][0]["priceChange1h"] if response else None
      priceChange1d = response["result"][0]["priceChange1d"] if response else None
      priceChange1w = response["result"][0]["priceChange1w"] if response else None

 except json.JSONDecodeError as e:
    print(f"{date_time} 'None' values registered {coin} : {e}")
    pass
 except (IndexError, KeyError) as e:
    print(f"{date_time} 'None' values registered {coin} : {e}")
    pass
 except Exception as e:
    print(f"{date_time} 'None' values registered {coin} : {e}")
    pass
 
 date = date_time
     
 try:
  
   cursor.executemany(f'''INSERT INTO {table_name} (date, price, volume, marketCap,
    availableSupply, totalSupply, fullyDilutedValuation, priceChange1h,
    priceChange1d, priceChange1w)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', [(date, price, volume, marketCap,
    availableSupply, totalSupply, fullyDilutedValuation, priceChange1h, priceChange1d,
    priceChange1w)])
                       
   conn.commit()
      
 except sqlite3.Error as e:
         print(f'Database insert error: {e}')
 
 finally:
   cursor.close()



def calculate_time() -> float:
 """
    Calculate the time remaining until 00:03 UTC.

    This function determines the number of seconds left until the next scheduled 
    update at 00:03, ensuring accurate synchronization with Alternative's data updates.

    If the current time is past 00:03, the function calculates the time remaining until 
    the same time on the next day.

    Returns:
        - float: The number of seconds left until 00:03.

    Example:
        >>> calculate_time()
        45782.5  # Time left in seconds
 """
 time_now = datetime.now(timezone.utc) 
 target_time = datetime.now(timezone.utc).replace(hour=0, minute=3, second=2)
 
 if time_now > target_time:                   
    target_time += timedelta(days=1)
 
 return (target_time - time_now).total_seconds()



def start_delay() -> int:
   """
    Calculate the delay time in seconds before starting the program.

    This function determines whether the program should wait one minute before execution
    to prevent conflicts with the `daily_sentiment()` function. If the current minute 
    ends in '3' or '8', it delays the start by 60 seconds; otherwise, it starts immediately.

    Returns:
        - int: The number of seconds to wait (either 60 or 0).

    Example:
        >>> delay = start_delay()
        >>> print(f"Waiting {delay} seconds before starting.")
   """
   minutes = str(datetime.now().minute)

   if minutes.endswith("3") or minutes.endswith("8"):
      print("Starting in 1 minute ...") 
      return 60
   
   else:
      return 0



## Main program

fng_value = None    #Initializing global sentiment, market_data will use it 
fng_name = None



async def hourly_sentiment():
   
   """
    Asynchronously fetches sentiment data every hour, aligned to a monotonic schedule with
    drift compensation.

    This coroutine introduces a 62-minute (3720 seconds) initial delay before its first execution 
    to avoid overlap with other data-fetching routines. After the initial wait, it calls 
    `fetch_sentiment()` every 3600 seconds (1 hour), using `time.monotonic()` to ensure interval 
    consistency and stability—even in the presence of system clock adjustments like NTP corrections.

    To preserve temporal alignment, the loop compares wall-clock and monotonic elapsed time:
        - If a significant discrepancy is detected (> ±0.1s), a drift correction is applied.
        - The correction is handled by subtracting the previous drift from `next_iter` 
          and applying the newly observed drift, keeping the cadence steady.

    Timing Strategy:
        - Monotonic-based interval pacing avoids issues from wall-clock adjustments.
        - Dynamically adjusts for system time drift via comparative delta tracking.
        - Uses `max(0, ...)` to ensure non-negative sleep intervals.

    Returns:
        - None. This coroutine runs indefinitely.

    Example:
        >>> await hourly_sentiment()
        # Starts after a 62-minute delay, then fetches sentiment data every hour precisely.
    """
     
  
   interval = 3600
   time_drift = 0

   next_iter = time.monotonic() + 3720                # Next iteration is in 1 hour 2 minutes
   sleep_time = max(0, next_iter - time.monotonic())
   await asyncio.sleep(sleep_time)                    # Initial sleep
              
   starting_time = datetime.now()
   starting_time_second = starting_time.second
   starting_monotonic = time.monotonic()     

   while True:   
        
        current_time = datetime.now()
        current_second = current_time.second
        current_monotonic = time.monotonic()

        await fetch_sentiment()

        if current_second != starting_time_second :
            next_iter -= time_drift
            wall_elapsed = (current_time - starting_time).total_seconds()
            mono_elapsed = current_monotonic - starting_monotonic
            time_drift = mono_elapsed - wall_elapsed

            if abs(time_drift) > 0.1:
                next_iter += time_drift

        next_iter += interval                             # Adds 60 minutes to the next_iter time 
        sleep_time = max(0, next_iter - time.monotonic())
        await asyncio.sleep(sleep_time) 



async def daily_sentiment():
   """
    Asynchronously fetch sentiment data every day at 00:03 UTC.

    This function runs an infinite loop that waits until the scheduled time (00:03) 
    before retrieving sentiment data using `fetch_sentiment()`. It calculates 
    the required sleep duration using `calculate_time()`, ensuring accurate execution 
    daily.

    Returns:
        - None: This function runs indefinitely and does not return a value.

    Example:
        >>> await daily_sentiment()
        >>> # The function will automatically fetch sentiment data every day at 00:03.
    """
   while True:
      sleeptime = calculate_time()
      await asyncio.sleep(sleeptime)
      await fetch_sentiment()
      

      
async def fetch_stack():
   """
    Asynchronously fetches market and cryptocurrency data every five minutes using a monotonic,
    drift-correcting schedule.

    This coroutine launches asynchronous data-gathering tasks for global market metrics,
    Bitcoin, and Ethereum at consistent 300-second intervals. It uses `time.monotonic()` for 
    timekeeping to avoid inaccuracies caused by system clock changes (e.g., NTP adjustments).

    Drift Handling:
        - Compares monotonic and wall-clock elapsed time to detect time drift.
        - Subtracts previously applied drift before recalculating the current one.
        - Applies a correction only if the drift exceeds ±0.1s, preserving interval accuracy
          while avoiding jitter from minor fluctuations.

    Timing Strategy:
        - Anchors execution to a monotonic interval, updated each cycle.
        - Sleep duration is calculated relative to `next_iter` to ensure consistent pacing.
        - `max(0, ...)` is used to prevent negative sleep values in edge cases.

    Data Sources:
        - `fetch_marketdata()`: Retrieves overall market metrics.
        - `fetch_coindata(url_btc, 'bitcoin', 'bitcoin_data')`: Fetches Bitcoin-specific data.
        - `fetch_coindata(url_eth, 'eth', 'eth_data')`: Fetches Ethereum-specific data.

    Returns:
        None. This coroutine runs indefinitely.

    Example:
        >>> await fetch_stack()
        # Repeatedly fetches and processes data every 5 minutes with monotonic precision and drift correction.
    """
   
   interval = 300
   time_drift = 0

   starting_time = datetime.now()
   starting_time_second = starting_time.second
   starting_monotonic = time.monotonic()           
   next_iter = starting_monotonic                  # Next iteration is now

   while True:
     
     current_time = datetime.now()
     current_second = current_time.second
     current_monotonic = time.monotonic()

     asyncio.create_task(fetch_marketdata())
     asyncio.create_task(fetch_coindata(url_btc, 'bitcoin', 'bitcoin_data'))
     asyncio.create_task(fetch_coindata(url_eth, 'eth', 'eth_data'))

     if current_second != starting_time_second :
        next_iter -= time_drift
        wall_elapsed = (current_time - starting_time).total_seconds()
        mono_elapsed = current_monotonic - starting_monotonic
        time_drift = mono_elapsed - wall_elapsed

        if abs(time_drift) > 0.1:
            next_iter += time_drift
    
     next_iter += interval                              # Adds 5 minutes to next_iter time
                                                      
     sleep_time = max(0, next_iter - time.monotonic())  # Time left until next_iter                                                                         
     await asyncio.sleep(sleep_time)



async def main():
   """
    Run the main event loop to manage concurrent tasks.

    This function initializes the program by introducing a delay (if necessary) using `start_delay()`, 
    ensuring smooth execution without conflicts. After retrieving sentiment data, it concurrently gathers 
    multiple asynchronous tasks using `asyncio.gather()`, enabling efficient execution of:

        - `fetch_stack()`: Fetches market, Bitcoin, and Ethereum data every five minutes.
        - `daily_sentiment()`: Retrieves sentiment data once a day at 00:03 UTC.
        - `hourly_sentiment()`: Fetches sentiment data every hour while avoiding synchronization issues.

    Returns:
        - None: The function runs indefinitely, managing all concurrent tasks.

    Example:
        >>> await main()
        >>> # This will continuously run all fetching functions within the event loop.
   """
   starting_delay = start_delay()
   await asyncio.sleep(starting_delay)
   await fetch_sentiment()
   await asyncio.gather(
      fetch_stack(),
      daily_sentiment(),
      hourly_sentiment(),
   )
 


if __name__ == '__main__':
 
 asyncio.run(main())




  
  
  
















