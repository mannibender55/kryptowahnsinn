import requests
import os
import json
from datetime import datetime, timedelta

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

def search_youtube(query, max_results=10, order="relevance", published_after=None):
    if not YOUTUBE_API_KEY:
        return {"error": "Missing YOUTUBE_API_KEY environment variable."}

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "order": order,
        "key": YOUTUBE_API_KEY
    }
    
    if published_after:
        params["publishedAfter"] = published_after

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        videos = []
        for item in data.get("items", []):
            snippet = item["snippet"]
            video_id = item["id"]["videoId"]
            
            videos.append({
                "title": snippet["title"],
                "channel": snippet["channelTitle"],
                "published_at": snippet["publishedAt"],
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "description": snippet.get("description", "")
            })
            
        return videos

    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Test: Crypto Trading Strategies (Last 30 Days)
    # Calculate date 30 days ago
    date_30_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat("T") + "Z"
    
    print(f"Searching for 'Crypto Trading Strategy' since {date_30_days_ago}...")
    results = search_youtube("Crypto Trading Strategy", max_results=5, order="viewCount", published_after=date_30_days_ago)
    print(json.dumps(results, indent=2))
