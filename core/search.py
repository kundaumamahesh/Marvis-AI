import asyncio
import urllib.request
import json

class WebSearchEngine:
    @staticmethod
    def search_sync(query: str, max_results: int = 3) -> str:
        """Uses an open public endpoint API to retrieve data without getting bot-blocked."""
        try:
            # Clean the query for the URL string
            clean_query = urllib.parse.quote(query)
            
            # If the user is asking for weather, route them to an open public weather API directly!
            if "weather" in query.lower():
                # Extract a potential city name default or check Mangalagiri
                city = "Mangalagiri" if "mangalagiri" in query.lower() else "Vijayawada"
                
                # Query a free, open-source weather data api that never blocks python IPs
                url = f"https://wttr.in/{city}?format=j1"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    current = data['current_condition'][0]
                    temp = current['temp_C']
                    desc = current['weatherDesc'][0]['value']
                    humidity = current['humidity']
                    wind = current['windspeedKmph']
                    
                    return f"[1] Real-time Weather Report for {city}\nURL: https://wttr.in\nContext: Current temperature is {temp}°C. Condition: {desc}. Humidity: {humidity}%. Wind Speed: {wind} km/h."

            # Fallback for standard general knowledge queries using open-source Wikipedia engine
            url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={clean_query}&limit={max_results}&namespace=0&format=json"
            req = urllib.request.Request(url, headers={'User-Agent': 'MARVIS-AI-Bot/1.0'})
            
            with urllib.request.urlopen(req, timeout=5) as response:
                raw_data = json.loads(response.read().decode())
                titles = raw_data[1]
                descriptions = raw_data[2]
                links = raw_data[3]
                
                if not titles:
                    return ""
                    
                context_blocks = []
                for i in range(len(titles)):
                    context_blocks.append(f"[{i+1}] {titles[i]}\nURL: {links[i]}\nContext: {descriptions[i]}\n")
                
                return "\n".join(context_blocks)
                
        except Exception as e:
            print(f"[SEARCH ENGINE WARNING] Open search fallback failed: {str(e)}")
            return ""

    @staticmethod
    def search(query: str, max_results: int = 3):
        """Asynchronous execution context wrapper."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, WebSearchEngine.search_sync, query, max_results)