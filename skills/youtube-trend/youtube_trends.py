import requests
import os
import json

# --- Configuration ---
# API Key must be set in env or passed
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

def get_trending_videos(region_code="DE", max_results=10, category_id=None):
    """
    Fetches trending videos from YouTube Data API v3.
    """
    if not YOUTUBE_API_KEY:
        return {"error": "Missing YOUTUBE_API_KEY environment variable."}

    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,statistics,contentDetails",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY
    }
    
    if category_id:
        params["videoCategoryId"] = category_id

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        videos = []
        for item in data.get("items", []):
            snippet = item["snippet"]
            stats = item["statistics"]
            video_id = item["id"]
            
            videos.append({
                "title": snippet["title"],
                "channel": snippet["channelTitle"],
                "views": stats.get("viewCount", 0),
                "likes": stats.get("likeCount", 0),
                "published_at": snippet["publishedAt"],
                "url": f"https://www.youtube.com/watch?v={video_id}"
            })
            
        return videos

    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Test run
    # To run this, export YOUTUBE_API_KEY=...
    print("Fetching trending videos...")
    trends = get_trending_videos()
    print(json.dumps(trends, indent=2))
