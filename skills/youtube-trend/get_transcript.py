from youtube_transcript_api import YouTubeTranscriptApi
import sys
import json

def get_transcript(video_id):
    try:
        # Use the class method correctly
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try finding manually created first
        try:
            transcript = transcript_list.find_manually_created_transcript(['en', 'de'])
        except:
            # Fallback to generated
            try:
                transcript = transcript_list.find_generated_transcript(['en', 'de'])
            except:
                 # Last resort: just get first available
                 transcript = transcript_list[0]

        data = transcript.fetch()
        full_text = " ".join([entry['text'] for entry in data])
        return full_text
        
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 get_transcript.py <video_id>")
        sys.exit(1)
        
    vid_id = sys.argv[1]
    if "v=" in vid_id:
        vid_id = vid_id.split("v=")[1].split("&")[0]
    elif "youtu.be/" in vid_id:
        vid_id = vid_id.split("youtu.be/")[1].split("?")[0]
        
    print(get_transcript(vid_id))
