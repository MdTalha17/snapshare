from fastapi import FastAPI, HTTPException
from src.schemas import PostCreate, PostResponse

app = FastAPI()


text_posts = {
    1: {"title": "Sunset Vibes", "content": "Captured this beautiful sunset today! 🌅"},
    2: {"title": "Coffee Time", "content": "Nothing beats a fresh cup of coffee in the morning. ☕"},
    3: {"title": "Mountain Adventure", "content": "Hiking through the mountains was an unforgettable experience."},
    4: {"title": "Coding Session", "content": "Spent the day building a FastAPI application. 💻"},
    5: {"title": "Beach Day", "content": "Enjoying the waves and the sunshine! 🌊"},
    6: {"title": "Workout Complete", "content": "Finished a great workout. Feeling energized! 💪"},
    7: {"title": "Delicious Dinner", "content": "Tried a new pasta recipe tonight. 🍝"},
    8: {"title": "Movie Night", "content": "Watching a classic sci-fi movie this evening. 🎬"},
    9: {"title": "Reading Time", "content": "Started reading a new book on machine learning. 📚"},
    10: {"title": "Weekend Getaway", "content": "Exploring a new city this weekend. ✈️"}
}


@app.get("/posts")
def get_all_posts(limit: int = None):
    if limit: 
        return list(text_posts.values())[:limit]
    return text_posts

@app.get("/posts/{post_id}")
def get_post(post_id: int) -> list[PostResponse]:
    if post_id not in text_posts:
        raise HTTPException(status_code=404, detail="Post not found.")
    return text_posts.get(post_id)

@app.post("/posts")
def create_post(post: PostCreate) -> PostCreate:
    new_post = {"title": post.title, "content": post.content}
    text_posts[max(text_posts.keys())+1] = new_post
    return new_post
